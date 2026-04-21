"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { platformCreateTenantRequest } from "@/lib/api";

export default function CreateTenantPage() {
  const { hasRole } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState({
    name: "",
    code: "",
    admin_email: "",
    admin_full_name: "",
    admin_password: "",
    confirm_password: "",
    approval_status: "approved",
    is_active: true,
  });

  useEffect(() => {
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
    }
  }, [hasRole, router]);

  if (!hasRole("platform_owner")) {
    return null;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (formData.admin_password !== formData.confirm_password) {
      setError("Passwords do not match");
      return;
    }

    if (formData.admin_password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);

    const { confirm_password, ...submitData } = formData;
    const res = await platformCreateTenantRequest(submitData);

    setLoading(false);

    if (res.ok) {
      setSuccess(true);
      setTimeout(() => {
        router.push("/platform");
      }, 2000);
    } else {
      setError(res.error || "Failed to create company");
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">
          Create New Company
        </h1>
        <Button variant="secondary" onClick={() => router.push("/platform")}>
          Cancel
        </Button>
      </div>

      {success && (
        <div className="mb-4 rounded-lg bg-emerald-500/10 p-4 text-emerald-400">
          Company created successfully! Redirecting...
        </div>
      )}

      {error && (
        <div className="mb-4 rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      <Card title="Company Information">
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            id="name"
            label="Company Name"
            value={formData.name}
            onChange={(e) =>
              setFormData({ ...formData, name: e.target.value })
            }
            required
          />

          <Input
            id="code"
            label="Company Code"
            value={formData.code}
            onChange={(e) =>
              setFormData({ ...formData, code: e.target.value.toLowerCase() })
            }
            required
            pattern="[a-z0-9_-]+"
            title="Only lowercase letters, numbers, hyphens, and underscores"
          />
          <p className="text-xs text-slate-500">
            Used for login. Only lowercase letters, numbers, hyphens, and
            underscores.
          </p>

          <div className="border-t border-slate-700 pt-4">
            <h3 className="mb-4 text-lg font-medium text-slate-200">
              Admin User
            </h3>

            <Input
              id="admin_full_name"
              label="Admin Full Name"
              value={formData.admin_full_name}
              onChange={(e) =>
                setFormData({ ...formData, admin_full_name: e.target.value })
              }
              required
            />

            <Input
              id="admin_email"
              type="email"
              label="Admin Email"
              value={formData.admin_email}
              onChange={(e) =>
                setFormData({ ...formData, admin_email: e.target.value })
              }
              required
            />

            <Input
              id="admin_password"
              type="password"
              label="Admin Password"
              value={formData.admin_password}
              onChange={(e) =>
                setFormData({ ...formData, admin_password: e.target.value })
              }
              required
              minLength={8}
            />

            <Input
              id="confirm_password"
              type="password"
              label="Confirm Password"
              value={formData.confirm_password}
              onChange={(e) =>
                setFormData({ ...formData, confirm_password: e.target.value })
              }
              required
            />
          </div>

          <div className="border-t border-slate-700 pt-4">
            <h3 className="mb-4 text-lg font-medium text-slate-200">
              Settings
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-2 block text-sm text-slate-400">
                  Approval Status
                </label>
                <select
                  id="approval_status"
                  value={formData.approval_status}
                  onChange={(e) =>
                    setFormData({ ...formData, approval_status: e.target.value })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-200"
                >
                  <option value="approved">Approved</option>
                  <option value="pending">Pending</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm text-slate-400">
                  Active Status
                </label>
                <select
                  id="is_active"
                  value={formData.is_active ? "true" : "false"}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      is_active: e.target.value === "true",
                    })
                  }
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-slate-200"
                >
                  <option value="true">Active</option>
                  <option value="false">Suspended</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex gap-4 pt-4">
            <Button type="submit" disabled={loading || success}>
              {loading ? "Creating..." : "Create Company"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push("/platform")}
              disabled={loading}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
