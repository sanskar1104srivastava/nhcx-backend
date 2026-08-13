import { apiClient, buildUrl } from './apiClient';
import {
  API_ENDPOINTS,
  setToken,
  setRefreshToken,
  getRefreshToken,
  clearSession,
  StoredUser,
} from './apiConfig';

const BASE = API_ENDPOINTS.auth;

// Mirrors the main Sahai app's auth contract exactly — NHCX signs in against
// the same `auth` Lambda, so these field names must match what that backend
// sends. Do not rename them here without changing the backend too.
export interface HospitalContext {
  hospitalId: string;
  name: string;
  address?: string;
  mobile?: string;
  email?: string;
  beds?: number;
  departments: string[];
  doctors: Array<{ doctorId: string; name: string; specialization?: string; department?: string }>;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  user?: StoredUser;
  hospital?: HospitalContext;
}

export interface HospitalCandidate {
  hospitalId: string;
  hospitalName: string;
  role?: string;
}

// verifyOtp returns EITHER a real session (accessToken present) OR, when the
// same mobile is active at 2+ hospitals, a "pick one" response with no token
// yet — selectionToken is then exchanged via selectHospital().
export interface OtpVerifyResponse extends Partial<LoginResponse> {
  multipleHospitals?: boolean;
  candidates?: HospitalCandidate[];
  selectionToken?: string;
}

export interface OtpRequestResponse {
  otpId: string;
}

// Both tokens always arrive together and are stored as a pair, so a stale
// refresh token can never outlive the access token it was issued alongside
// (rotation invalidates the pair as a unit).
function storeSession(data: Partial<LoginResponse>) {
  if (data.accessToken) setToken(data.accessToken);
  if (data.refreshToken) setRefreshToken(data.refreshToken);
}

const authService = {
  requestOtp: (mobile: string) =>
    apiClient.post<OtpRequestResponse>(buildUrl(BASE, '/auth/login/otp/request'), { mobile }),

  verifyOtp: async (mobile: string, otp: string, otpId?: string) => {
    const res = await apiClient.post<OtpVerifyResponse>(
      buildUrl(BASE, '/auth/login/otp/verify'),
      { mobile, otp, otpId },
    );
    storeSession(res.data);
    return res;
  },

  // Second step when a login comes back with multipleHospitals: true — the
  // user picks which hospital session to start.
  selectHospital: async (selectionToken: string, hospitalId: string) => {
    const res = await apiClient.post<LoginResponse>(
      buildUrl(BASE, '/auth/login/otp/select-hospital'),
      { selectionToken, hospitalId },
    );
    storeSession(res.data);
    return res;
  },

  // Email/password sign-in — same multi-hospital branch as OTP.
  loginWithPassword: async (email: string, password: string) => {
    const res = await apiClient.post<OtpVerifyResponse>(
      buildUrl(BASE, '/auth/login/password'),
      { email, password },
    );
    storeSession(res.data);
    return res;
  },

  // Google Sign-In — idToken is the credential Google Identity Services hands
  // back; the backend verifies it against Google's public keys before trusting
  // the email inside it.
  loginWithGoogle: async (idToken: string) => {
    const res = await apiClient.post<OtpVerifyResponse>(
      buildUrl(BASE, '/auth/login/google'),
      { idToken },
    );
    storeSession(res.data);
    return res;
  },

  getMe: () => apiClient.get<StoredUser>(buildUrl(BASE, '/auth/me')),

  logout: async () => {
    const refreshToken = getRefreshToken();
    try {
      // Best-effort server-side revocation; the local wipe below must happen
      // either way, so the user is signed out even if this call fails.
      await apiClient.post(buildUrl(BASE, '/auth/logout'), refreshToken ? { refreshToken } : {});
    } finally {
      clearSession();
    }
  },
};

export default authService;
