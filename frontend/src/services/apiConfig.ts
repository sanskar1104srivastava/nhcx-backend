import { secureGetItem, secureSetItem, secureRemoveItem } from './secureStorage';

// Same API Gateway as the main Sahai app — NHCX is a separate frontend on the
// same backend, so it signs in against the same `auth` Lambda. Override per
// environment with VITE_API_BASE_URL in .env.
const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  'https://1edaydqcf4.execute-api.ap-southeast-1.amazonaws.com';

export const WEBSOCKET_URL =
  (import.meta.env.VITE_WEBSOCKET_URL as string | undefined) ?? '';

// Every module sits behind the same gateway host; kept as a map so an NHCX
// module can be pointed at its own host later without touching call sites.
export const API_ENDPOINTS = {
  auth: API_BASE,
  nhcx: API_BASE,
  users: API_BASE,
  settings: API_BASE,
  hospitals: API_BASE,
} as const;

// Deliberately identical to the main Sahai app's keys (see its apiConfig.ts).
// NHCX authenticates against the same backend, so if the two apps are ever
// served from the same origin the session is shared and the user does not have
// to sign in twice. Change these only if you want NHCX sessions isolated —
// note secureStorage's SECRET must stay in sync for the values to decode.
export const TOKEN_KEY = 'sahai_access_token';
export const REFRESH_TOKEN_KEY = 'sahai_refresh_token';
export const USER_KEY = 'Sahai_user';

export function getToken(): string | null {
  return secureGetItem<string>(TOKEN_KEY);
}
export function setToken(token: string): void {
  secureSetItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  secureRemoveItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return secureGetItem<string>(REFRESH_TOKEN_KEY);
}
export function setRefreshToken(token: string): void {
  secureSetItem(REFRESH_TOKEN_KEY, token);
}
export function clearRefreshToken(): void {
  secureRemoveItem(REFRESH_TOKEN_KEY);
}

export interface StoredUser {
  userId: string;
  name?: string;
  email?: string;
  mobile?: string;
  role: string;
  roles?: string[];
  hospitalId?: string;
  doctorId?: string;
}

export function getUser(): StoredUser | null {
  return secureGetItem<StoredUser>(USER_KEY);
}
export function setUser(user: StoredUser): void {
  secureSetItem(USER_KEY, user);
}
export function clearUser(): void {
  secureRemoveItem(USER_KEY);
}

/** Wipe every credential this app owns. Call on logout and on a failed refresh. */
export function clearSession(): void {
  clearToken();
  clearRefreshToken();
  clearUser();
}
