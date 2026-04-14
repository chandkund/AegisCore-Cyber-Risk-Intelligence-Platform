"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { hasSession } from "@/lib/auth-storage";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(hasSession() ? "/dashboard" : "/login");
  }, [router]);
  return (
    <div
      className="flex min-h-screen items-center justify-center text-slate-500"
      role="status"
      aria-live="polite"
    >
      Loading…
    </div>
  );
}
