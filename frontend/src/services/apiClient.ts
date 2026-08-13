import { API_ENDPOINTS } from './apiConfig';

const TOKEN_KEY = 'nhcx_session_token';

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || '';
}
export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}
export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) ?? {}),
  };

  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  const json = await res.json();
  if (!res.ok) {
    const detail = json.detail
      ? Array.isArray(json.detail)
        ? json.detail.map((d: any) => `${d.loc?.join('.')}: ${d.msg}`).join('; ')
        : String(json.detail)
      : undefined;
    throw Object.assign(new Error(json.message || detail || `HTTP ${res.status}`), {
      status: res.status,
    });
  }
  return json as ApiResponse<T>;
}

export function buildUrl(
  base: string,
  path: string,
  params?: Record<string, string | number | undefined>,
): string {
  const url = new URL(`${base}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
    });
  }
  return url.toString();
}

export const apiClient = {
  get: <T>(url: string) => request<T>(url),
  post: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(url: string, body: unknown) =>
    request<T>(url, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),
};
