"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  platformTenantDetailRequest,
  platformTenantAdminsRequest,
  platformUpdateTenantRequest,
  platformResetAdminPasswordRequest,
} from "@/lib/api";
import type {
  TenantDetailOut,
  TenantAdminOut,
  TenantUpdate,
} from "@/types/api";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function TenantDetailPage({ params }: PageProps) {
  const { user, hasRole } = useAuth();
  const router = useRouter();
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [tenant, setTenant] = useState<TenantDetailOut | null>(null);
  const [admins, setAdmins] = useState<TenantAdminOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState<string | null>(null);

  useEffect(() => {
    params.then((p) => setTenantId(p.id));
  }, [params]);

  useEffect(() => {
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
      return;
    }
    if (!tenantId) return;

    async function loadData() {
      try {
        const [tenantRes, adminsRes] = await Promise.all([
          platformTenantDetailRequest(tenantId!),
          platformTenantAdminsRequest(tenantId!),
        ]);
        if (tenantRes.ok && tenantRes.data) {
          setTenant(tenantRes.data);
        }
        if (adminsRes.ok && adminsRes.data) {
          setAdmins(adminsRes.data);
        }
      } catch (err) {
        setError("Failed to load company data");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [hasRole, router, tenantId]);

  async function updateTenant(updates: TenantUpdate) {
    if (!tenantId) return;
    setSaving(true);
    const res = await platformUpdateTenantRequest(tenantId, updates);
    if (res.ok) {
      // Reload data
      const tenantRes = await platformTenantDetailRequest(tenantId);
      if (tenantRes.ok && tenantRes.data) {
        setTenant(tenantRes.data);
      }
    }
    setSaving(false);
  }

  async function resetPassword(adminId: string, newPassword: string) {
    if (!tenantId) return;
    setResetting(adminId);
    const res = await platformResetAdminPasswordRequest(
      tenantId,
      adminId,
      newPassword
    );
    if (res.ok) {
      alert("Password reset successfully");
    } else {
      alert("Failed to reset password: " + (res.error || "Unknown error"));
    }
    setResetting(null);
  }

  if (!hasRole("platform_owner")) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-slate-400">
        Loading company data…
      </div>
    );
  }

  if (!tenant) {
    return (
      <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
        Company not found
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">
            {tenant.name}
          </h1>
          <p className="text-slate-400">Code: {tenant.code}</p>
        </div>
        <Button variant="secondary" onClick={() => router.push("/platform")}>
          Back to Platform
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      {/* Company Status */}
      <Card title="Company Status">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-slate-400">Active Status</p>
            <div className="mt-2 flex items-center gap-2">
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
                  tenant.is_active
                    ? "bg-emerald-500/10 text-emerald-400"
                    : "bg-rose-500/10 text-rose-400"
                }`}
              >
                {tenant.is_active ? "Active" : "Suspended"}
              </span>
              <Button
                variant="secondary"
                onClick={() =>
                  updateTenant({ is_active: !tenant.is_active })
                }
                disabled={saving}
              >
                {tenant.is_active ? "Suspend" : "Activate"}
              </Button>
            </div>
          </div>
          <div>
            <p className="text-sm text-slate-400">Approval Status</p>
            <div className="mt-2 flex items-center gap-2">
              <ApprovalBadge status={tenant.approval_status} />
              {tenant.approval_status === "pending" && (
                <Button
                  variant="secondary"
                  onClick={() =>
                    updateTenant({
                      approval_status: "approved",
                      approval_notes: "Approved by platform owner",
                    })
                  }
                  disabled={saving}
                >
                  Approve
                </Button>
              )}
              {tenant.approval_status !== "rejected" && (
                <Button
                  variant="secondary"
                  onClick={() =>
                    updateTenant({
                      approval_status: "rejected",
                      approval_notes: "Rejected by platform owner",
                    })
                  }
                  disabled={saving}
                >
                  Reject
                </Button>
              )}
            </div>
          </div>
        </div>
        <div className="mt-4 text-sm text-slate-400">
          <p>Created: {new Date(tenant.created_at).toLocaleString()}</p>
          {tenant.approved_at && (
            <p>Approved: {new Date(tenant.approved_at).toLocaleString()}</p>
          )}
          {tenant.approved_by && <p>Approved by: {tenant.approved_by}</p>}
          {tenant.approval_notes && (
            <p className="mt-2">Notes: {tenant.approval_notes}</p>
          )}
        </div>
      </Card>

      {/* Company Stats */}
      <Card title="Company Statistics">
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Total Users</p>
            <p className="text-2xl font-semibold text-slate-100">
              {tenant.user_count}
            </p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Admins</p>
            <p className="text-2xl font-semibold text-slate-100">
              {admins.length}
            </p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Status</p>
            <p className="text-lg font-medium text-slate-100">
              {tenant.is_active ? "Active" : "Suspended"}
            </p>
          </div>
        </div>
      </Card>

      {/* Admin Users */}
      <Card title="Company Administrators">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-700">
              <tr>
                <th className="pb-3 font-medium text-slate-400">Name</th>
                <th className="pb-3 font-medium text-slate-400">Email</th>
                <th className="pb-3 font-medium text-slate-400">Status</th>
                <th className="pb-3 font-medium text-slate-400">Created</th>
                <th className="pb-3 font-medium text-slate-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {admins.map((admin) => (
                <tr key={admin.id}>
                  <td className="py-3 text-slate-200">{admin.full_name}</td>
                  <td className="py-3 text-slate-400">{admin.email}</td>
                  <td className="py-3">
                    <StatusBadge active={admin.is_active} />
                  </td>
                  <td className="py-3 text-slate-400">
                    {new Date(admin.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3">
                    <Button
                      variant="secondary"
                      onClick={() => {
                        const newPassword = prompt(
                          "Enter new password (min 8 chars):"
                        );
                        if (newPassword && newPassword.length >= 8) {
                          resetPassword(admin.id, newPassword);
                        }
                      }}
                      disabled={resetting === admin.id}
                    >
                      {resetting === admin.id ? "Resetting…" : "Reset Password"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {admins.length === 0 && (
          <p className="py-4 text-center text-slate-400">No admins found</p>
        )}
      </Card>
    </div>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400">
      Active
    </span>
  ) : (
    <span className="inline-flex items-center rounded-full bg-rose-500/10 px-2 py-1 text-xs font-medium text-rose-400">
      Inactive
    </span>
  );
}

function ApprovalBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    approved: "bg-emerald-500/10 text-emerald-400",
    pending: "bg-amber-500/10 text-amber-400",
    rejected: "bg-rose-500/10 text-rose-400",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
        colors[status] || "bg-slate-500/10 text-slate-400"
      }`}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
