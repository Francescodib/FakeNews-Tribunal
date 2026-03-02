"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  clearTokens,
  getAccessToken,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  saveTokens,
} from "./api";

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsAuthenticated(!!getAccessToken());
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password);
    saveTokens(tokens.access_token, tokens.refresh_token);
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const tokens = await apiRegister(email, password);
    saveTokens(tokens.access_token, tokens.refresh_token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    clearTokens();
    setIsAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
