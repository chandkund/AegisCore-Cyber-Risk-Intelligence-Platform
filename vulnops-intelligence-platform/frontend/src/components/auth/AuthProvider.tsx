"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { clearTokens, hasSession, setTokens } from "@/lib/auth-storage";
import { loginRequest, logoutRequest, meRequest } from "@/lib/api";
import type { MeResponse } from "@/types/api";

type AuthContextValue = {
  user: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (role: string) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!hasSession()) {
      setUser(null);
      return;
    }
    const me = await meRequest();
    setUser(me);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!hasSession()) {
        if (!cancelled) setLoading(false);
        return;
      }
      const me = await meRequest();
      if (!cancelled) {
        if (!me) clearTokens();
        setUser(me);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const r = await loginRequest(email, password);
    if (!r.ok || !r.tokens) return { ok: false as const, error: r.error };
    setTokens(r.tokens.access_token, r.tokens.refresh_token);
    const me = await meRequest();
    setUser(me);
    return { ok: true as const };
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
  }, []);

  const hasRole = useCallback(
    (role: string) => !!user?.roles?.includes(role),
    [user]
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      refreshUser,
      hasRole,
    }),
    [user, loading, login, logout, refreshUser, hasRole]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
