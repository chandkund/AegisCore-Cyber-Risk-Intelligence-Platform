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
import { clearSession, hasSession, setSessionActive } from "@/lib/auth-storage";
import { loginRequest, logoutRequest, meRequest } from "@/lib/api";
import type { MeResponse } from "@/types/api";

type AuthContextValue = {
  user: MeResponse | null;
  loading: boolean;
  login: (companyCode: string, email: string, password: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  hasRole: (role: string) => boolean;
  setTokensFromRegistration?: (access: string, refresh: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!hasSession()) {
        if (!cancelled) setLoading(false);
        return;
      }
      const me = await meRequest();
      if (!cancelled) {
        if (!me) clearSession();
        setUser(me);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (companyCode: string, email: string, password: string) => {
    const r = await loginRequest(companyCode, email, password);
    if (!r.ok || !r.data) return { ok: false as const, error: r.error };
    // Session is marked active via setSessionActive() in loginRequest
    // Tokens are in HTTPOnly cookies, not JavaScript
    const me = await meRequest();
    setUser(me);
    return { ok: true as const };
  }, []);

  /** @deprecated Registration now uses cookie-based auth */
  const setTokensFromRegistration = useCallback((_access: string, _refresh: string) => {
    // With cookie-based auth, registration response sets cookies
    // Just need to mark session active
    setSessionActive();
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      // Server clears HTTPOnly cookies; we clear local session state
      clearSession();
      setUser(null);
    }
  }, []);

  const hasRole = useCallback(
    (role: string) => !!user?.roles?.includes(role),
    [user]
  );

  const refreshUser = useCallback(async () => {
    const me = await meRequest();
    setUser(me);
    if (!me) clearSession();
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      refreshUser,
      hasRole,
      setTokensFromRegistration,
    }),
    [user, loading, login, logout, refreshUser, hasRole, setTokensFromRegistration]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
