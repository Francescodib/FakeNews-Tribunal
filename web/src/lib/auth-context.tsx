"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  clearTokens,
  getAccessToken,
  getMe,
  getRefreshToken,
  login as apiLogin,
  logout as apiLogout,
  refreshTokens,
  register as apiRegister,
  saveTokens,
  type Me,
} from "./api";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: Me | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/** Decode the `exp` claim (seconds) from a JWT without verifying the signature. */
function getTokenExpiryMs(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof decoded.exp === "number" ? decoded.exp * 1000 : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<Me | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /** Schedule a proactive token refresh 60 s before the access token expires. */
  const scheduleRefresh = useCallback((accessToken: string) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const expiry = getTokenExpiryMs(accessToken);
    if (!expiry) return;
    const delay = expiry - Date.now() - 60_000; // 1 min before expiry
    if (delay <= 0) return; // already too late — let the next API call handle 401
    refreshTimerRef.current = setTimeout(async () => {
      const rt = getRefreshToken();
      if (!rt) return;
      try {
        const tokens = await refreshTokens(rt);
        saveTokens(tokens.access_token, tokens.refresh_token);
        scheduleRefresh(tokens.access_token); // reschedule for the new token
      } catch {
        // Refresh failed (token revoked / server down) — force re-login
        clearTokens();
        setIsAuthenticated(false);
        setUser(null);
      }
    }, delay);
  }, []);

  const fetchUser = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      setIsAuthenticated(true);
      scheduleRefresh(token);
      fetchUser().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [fetchUser, scheduleRefresh]);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password);
    saveTokens(tokens.access_token, tokens.refresh_token);
    scheduleRefresh(tokens.access_token);
    setIsAuthenticated(true);
    const me = await getMe();
    setUser(me);
  }, [scheduleRefresh]);

  const register = useCallback(async (email: string, password: string) => {
    const tokens = await apiRegister(email, password);
    saveTokens(tokens.access_token, tokens.refresh_token);
    scheduleRefresh(tokens.access_token);
    setIsAuthenticated(true);
    const me = await getMe();
    setUser(me);
  }, [scheduleRefresh]);

  const logout = useCallback(async () => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    await apiLogout();
    clearTokens();
    setIsAuthenticated(false);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    await fetchUser();
  }, [fetchUser]);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
