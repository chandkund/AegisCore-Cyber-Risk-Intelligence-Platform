"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./AuthProvider";
import { hasSession } from "@/lib/auth-storage";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!hasSession() || !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div
        className="flex min-h-[50vh] items-center justify-center text-slate-400"
        role="status"
        aria-live="polite"
      >
        Authenticating…
      </div>
    );
  }

  if (!hasSession() || !user) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-slate-400">
        Redirecting to sign in…
      </div>
    );
  }

  return <>{children}</>;
}
