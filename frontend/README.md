# NHCX Frontend

React 18 + Vite 6 + React Router v7 SPA for the **NHCX** (National Health Claims
Exchange) module of Sahai. Deployed as its own app so NHCX pages and tabs stay
separate from the main hospital SPA, but it runs on the **same Sahai backend**
and authenticates against the **same `auth` Lambda**.

Ships with the full auth flow (OTP / email+password / Google), a
token-refreshing API client, and the shadcn-style Radix UI kit.

**Requires Node 20+.**

```bash
npm install
cp .env.example .env   # VITE_API_BASE_URL — same gateway as Sahai
npm run dev            # http://localhost:5173
npm run build          # typecheck + production build to dist/
```

## Relationship to the main Sahai app

| Concern | How NHCX handles it |
|---|---|
| Backend | Same API Gateway, same Lambdas. No separate backend. |
| Auth | Same `/auth/*` endpoints, same request/response field names (`hospitalId`, `multipleHospitals`, …). Do not rename these without changing the backend. |
| Session storage | **Same keys and same cipher secret** as Sahai (`sahai_access_token`, `sahai_refresh_token`, `Sahai_user`, `Sahai_hospital`). If both apps are served from one origin, signing into either signs you into both. |
| UI kit | Copy of Sahai's `components/ui/`. Keep in sync manually, or extract to a shared package later. |
| Pages | NHCX-only. Nothing from the hospital SPA is carried over. |

> To make NHCX sessions **isolated** instead of shared, change the three key
> names in `src/services/apiConfig.ts`. `SECRET` in `secureStorage.ts` must
> match Sahai's for a shared session to decode, so leave it alone unless you're
> deliberately separating them.

## Folder structure

```text
src/
├── main.tsx                     # entry — mounts <App />
├── vite-env.d.ts                # typed import.meta.env
├── app/
│   ├── App.tsx                  # ThemeProvider → AuthProvider → RouterProvider + Toaster
│   ├── routes.tsx               # createBrowserRouter; /login standalone, rest under MainLayout
│   ├── components/
│   │   ├── layouts/MainLayout.tsx   # sidebar + header + <Outlet />
│   │   ├── shared/ProtectedRoute.tsx
│   │   └── ui/                      # 46 Radix wrappers + cn() helper + use-mobile
│   └── pages/                       # one file per route — add NHCX pages here
│       ├── LoginPage.tsx
│       ├── DashboardPage.tsx        # placeholder
│       ├── SettingsPage.tsx         # placeholder
│       └── NotFoundPage.tsx
├── contexts/AuthContext.tsx     # session state, applySession(), logout()
├── services/                    # all network + storage access
│   ├── apiConfig.ts             # base URL, token/user storage keys
│   ├── apiClient.ts             # fetch wrapper, 401 refresh + retry queue
│   ├── authService.ts           # auth endpoints (mirrors Sahai's contract)
│   ├── secureStorage.ts         # tamper-evident localStorage wrapper
│   └── index.ts                 # barrel
├── hooks/                       # shared React hooks (empty)
├── config/                      # static config / constants (empty)
├── styles/                      # fonts.css → tailwind.css → theme.css
└── assets/
```

## Adding an NHCX page

1. Create `src/app/pages/XPage.tsx`.
2. Register it as a child of the protected route in `src/app/routes.tsx`.
3. Add a nav entry to `navItems` in `MainLayout.tsx`.

## Adding an API module

Create `src/services/xService.ts` following `authService.ts`: import
`apiClient` + `buildUrl`, resolve the host from `API_ENDPOINTS`, and export a
default object of named methods. Add the module's host to `API_ENDPOINTS` in
`apiConfig.ts` (an `nhcx` entry is already stubbed there).

## Auth flow

- **OTP:** `requestOtp(mobile)` → `verifyOtp(mobile, otp, otpId)`
- **Password:** `loginWithPassword(email, password)`
- **Google:** `loginWithGoogle(idToken)` — only rendered when `VITE_GOOGLE_CLIENT_ID` is set

Any of the three can return `multipleHospitals: true` with a `selectionToken`
and a candidate list instead of a session; the login page then shows a picker
and calls `selectHospital(selectionToken, hospitalId)`.

Access + refresh tokens are stored as a pair via `secureStorage`. On a 401 the
API client refreshes once, queues any concurrent requests behind that single
refresh, and replays them; if the refresh itself fails it clears the session and
redirects to `/login`.

> `secureStorage` obfuscates and checksums localStorage values to block casual
> DevTools tampering. It is client-side JS and is **not** a security boundary —
> the backend must authorise every request independently.

## Styling

Tailwind v4 via `@tailwindcss/vite`. Design tokens are CSS custom properties on
`:root` / `.dark` in `src/styles/theme.css`, aliased into Tailwind with
`@theme inline`. Use `cn()` from `src/app/components/ui/utils.ts` for
conditional classes. `@` resolves to `src/`.

## Deployment

SPA — configure the host to serve `index.html` as the 404/error document so
client-side routes work on direct URL access. Use a separate S3 bucket from the
main Sahai frontend.
