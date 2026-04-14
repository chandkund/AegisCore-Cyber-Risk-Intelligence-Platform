"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { hasSession } from "@/lib/auth-storage";

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user && hasSession()) router.replace("/dashboard");
  }, [loading, user, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const r = await login(email.trim(), password);
    setSubmitting(false);
    if (!r.ok) {
      setError(r.error || "Sign in failed");
      return;
    }
    router.replace("/dashboard");
  }

  if (loading) {
    return (
      <p className="text-center text-slate-500" role="status">
        Checking session…
      </p>
    );
  }

  return (
    <Card title="Sign in">
      <p className="mb-4 text-sm text-slate-400">
        Use credentials from <code className="text-sky-400">seed_oltp.py</code> (e.g. admin).
      </p>
      <form className="flex flex-col gap-4" onSubmit={onSubmit} noValidate>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          label="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          aria-invalid={!!error}
        />
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error ? (
          <p className="text-sm text-rose-400" role="alert">
            {error}
          </p>
        ) : null}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </Card>
  );
}
