"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { hasSession } from "@/lib/auth-storage";
import { acceptInvitationRequest } from "@/lib/api";

function AcceptInvitationForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { setTokensFromRegistration, user, loading } = useAuth();

  const token = searchParams.get("token");

  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!loading && user && hasSession()) router.replace("/dashboard");
  }, [loading, user, router]);

  function validate(): boolean {
    const newErrors: Record<string, string> = {};

    if (fullName.length < 2) {
      newErrors.fullName = "Full name must be at least 2 characters";
    }

    if (password.length < 12) {
      newErrors.password = "Password must be at least 12 characters";
    }

    if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});

    if (!validate()) return;

    if (!token) {
      setErrors({ form: "Invitation token is missing" });
      return;
    }

    setSubmitting(true);
    const r = await acceptInvitationRequest({
      invitation_token: token,
      full_name: fullName.trim(),
      password: password,
    });
    setSubmitting(false);

    if (!r.ok) {
      setErrors({ form: r.error || "Invitation acceptance failed" });
      return;
    }

    if (r.tokens) {
      setTokensFromRegistration?.(r.tokens.access_token, r.tokens.refresh_token);
    }
    setSuccess(true);
    setTimeout(() => router.replace("/dashboard"), 1500);
  }

  if (loading) {
    return (
      <p className="text-center text-slate-500" role="status">
        Checking session…
      </p>
    );
  }

  if (!token) {
    return (
      <Card title="Invalid Invitation">
        <div className="text-center py-6">
          <div className="mx-auto w-12 h-12 rounded-full bg-rose-500/20 flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-slate-100 mb-2">Invalid Invitation Link</h3>
          <p className="text-sm text-slate-400">
            The invitation link is missing or invalid. Please check your email for the correct link.
          </p>
        </div>
      </Card>
    );
  }

  if (success) {
    return (
      <Card title="Welcome to AegisCore">
        <div className="text-center py-6">
          <div className="mx-auto w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-slate-100 mb-2">Account Created!</h3>
          <p className="text-sm text-slate-400">
            Your account has been created successfully. Welcome to your company workspace.
          </p>
          <p className="text-sm text-slate-500 mt-2">Redirecting to dashboard…</p>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Accept Invitation">
      <p className="mb-4 text-sm text-slate-400">
        You&apos;ve been invited to join a company workspace. Create your account to get started.
      </p>
      <form className="flex flex-col gap-4" onSubmit={onSubmit} noValidate>
        {errors.form ? (
          <div className="p-3 rounded-md bg-rose-500/10 border border-rose-500/20">
            <p className="text-sm text-rose-400" role="alert">
              {errors.form}
            </p>
          </div>
        ) : null}

        <div className="space-y-1">
          <Input
            id="fullName"
            name="fullName"
            type="text"
            autoComplete="name"
            label="Full Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            aria-invalid={!!errors.fullName}
          />
          {errors.fullName ? (
            <p className="text-xs text-rose-400">{errors.fullName}</p>
          ) : null}
        </div>

        <div className="space-y-1">
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="new-password"
            label="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            aria-invalid={!!errors.password}
          />
          {errors.password ? (
            <p className="text-xs text-rose-400">{errors.password}</p>
          ) : (
            <p className="text-xs text-slate-500">Minimum 12 characters</p>
          )}
        </div>

        <div className="space-y-1">
          <Input
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            autoComplete="new-password"
            label="Confirm Password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            aria-invalid={!!errors.confirmPassword}
          />
          {errors.confirmPassword ? (
            <p className="text-xs text-rose-400">{errors.confirmPassword}</p>
          ) : null}
        </div>

        <Button type="submit" disabled={submitting} className="mt-2">
          {submitting ? "Creating Account…" : "Accept Invitation"}
        </Button>
      </form>
    </Card>
  );
}

export default function AcceptInvitationPage() {
  return (
    <Suspense fallback={<p className="text-center text-slate-500">Loading…</p>}>
      <AcceptInvitationForm />
    </Suspense>
  );
}
