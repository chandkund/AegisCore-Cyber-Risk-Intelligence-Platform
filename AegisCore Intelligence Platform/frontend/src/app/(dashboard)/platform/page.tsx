"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { platformMetricsRequest, platformTenantsRequest } from "@/lib/api";
import type { TenantOut, PlatformMetricsOut } from "@/types/api";

export default function PlatformDashboardPage() {
  const { user, hasRole } = useAuth();
  const router = useRouter();
  const [metrics, setMetrics] = useState<PlatformMetricsOut | null>(null);
  const [tenants, setTenants] = useState<TenantOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Only platform_owner can access this page
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
      return;
    }

    async function loadData() {
      try {
        const [metricsRes, tenantsRes] = await Promise.all([
          platformMetricsRequest(),
          platformTenantsRequest(),
        ]);
        if (metricsRes.ok && metricsRes.data) {
          setMetrics(metricsRes.data);
        }
        if (tenantsRes.ok && tenantsRes.data) {
          setTenants(tenantsRes.data.items || []);
        }
      } catch (err) {
        setError("Failed to load platform data");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [hasRole, router]);

  if (!hasRole("platform_owner")) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-slate-400">
        Loading platform data…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Platform Management</h1>
        <Button onClick={() => router.push("/platform/tenants/new")}>
          + Create Company
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      {/* Metrics Overview */}
      {metrics && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            title="Total Companies"
            value={metrics.total_tenants}
            subtitle={`${metrics.active_tenants} active`}
          />
          <MetricCard
            title="Pending Approval"
            value={metrics.pending_tenants}
            subtitle={`${metrics.rejected_tenants} rejected`}
          />
          <MetricCard
            title="Total Users"
            value={metrics.total_users}
            subtitle={`${metrics.active_users} active`}
          />
          <MetricCard
            title="Invitations"
            value={metrics.total_invitations_sent}
            subtitle={`${metrics.pending_invitations} pending`}
          />
        </div>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <QuickActionCard
          title="Upload Monitoring"
          description="View data imports and file uploads across all companies"
          icon="☁️"
          onClick={() => router.push("/platform/uploads")}
        />
        <QuickActionCard
          title="Storage Overview"
          description="Monitor storage usage and distribution by company"
          icon="💾"
          onClick={() => router.push("/platform/storage")}
        />
        <QuickActionCard
          title="Audit Logs"
          description="Review platform activity and security events"
          icon="🛡️"
          onClick={() => router.push("/platform/audit")}
        />
      </div>

      {/* Recent Signups */}
      {metrics && (
        <Card title="Recent Activity">
          <div className="grid grid-cols-2 gap-4">
            <div className="rounded-lg bg-slate-800/50 p-4">
              <p className="text-sm text-slate-400">New Companies (7 days)</p>
              <p className="text-2xl font-semibold text-slate-100">
                {metrics.recent_signups_7d}
              </p>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-4">
              <p className="text-sm text-slate-400">New Companies (30 days)</p>
              <p className="text-2xl font-semibold text-slate-100">
                {metrics.recent_signups_30d}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Companies Table */}
      <Card title="Recent Companies">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-700">
              <tr>
                <th className="pb-3 font-medium text-slate-400">Name</th>
                <th className="pb-3 font-medium text-slate-400">Code</th>
                <th className="pb-3 font-medium text-slate-400">Status</th>
                <th className="pb-3 font-medium text-slate-400">Approval</th>
                <th className="pb-3 font-medium text-slate-400">Created</th>
                <th className="pb-3 font-medium text-slate-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {tenants.slice(0, 10).map((tenant) => (
                <tr key={tenant.id}>
                  <td className="py-3 text-slate-200">{tenant.name}</td>
                  <td className="py-3 text-slate-400">{tenant.code}</td>
                  <td className="py-3">
                    <StatusBadge active={tenant.is_active} />
                  </td>
                  <td className="py-3">
                    <ApprovalBadge status={tenant.approval_status} />
                  </td>
                  <td className="py-3 text-slate-400">
                    {new Date(tenant.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => router.push(`/platform/tenants/${tenant.id}`)}
                    >
                      View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {tenants.length > 10 && (
          <div className="mt-4 text-center">
            <Button
              variant="secondary"
              onClick={() => router.push("/platform/tenants")}
            >
              View All Companies
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: number;
  subtitle: string;
}) {
  return (
    <div className="rounded-lg bg-slate-800/50 p-4">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="mt-1 text-3xl font-semibold text-slate-100">{value}</p>
      <p className="text-xs text-slate-500">{subtitle}</p>
    </div>
  );
}

function QuickActionCard({
  title,
  description,
  icon,
  onClick,
}: {
  title: string;
  description: string;
  icon: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-start gap-4 rounded-lg bg-slate-800/50 p-4 text-left transition-colors hover:bg-slate-800"
    >
      <span className="text-2xl">{icon}</span>
      <div>
        <h3 className="font-medium text-slate-200">{title}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
    </button>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400">
      Active
    </span>
  ) : (
    <span className="inline-flex items-center rounded-full bg-rose-500/10 px-2 py-1 text-xs font-medium text-rose-400">
      Suspended
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
