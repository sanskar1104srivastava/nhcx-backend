import { createContext, useContext, useMemo, useState, ReactNode } from 'react';
import { getToken, setToken as storeToken, clearToken } from '../services/apiClient';
import { API_ENDPOINTS } from '../services/apiConfig';

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthCtx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [hasToken, setHasToken] = useState<boolean>(() => Boolean(getToken()));

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const res = await fetch(`${API_ENDPOINTS.nhcx}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      if (data.ok && data.token) {
        storeToken(data.token);
        setHasToken(true);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  };

  const logout = () => {
    clearToken();
    setHasToken(false);
  };

  const value = useMemo(() => ({ isAuthenticated: hasToken, login, logout }), [hasToken]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error('useAuth must be inside <AuthProvider>');
  return ctx;
}
