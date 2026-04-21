"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { platformTenantsRequest } from "@/lib/api";
import type { TenantOut } from "@/types/api";

export default function PlatformTenantsPage() {
  const { hasRole } = useAuth();
  const router = useRouter();
  const [tenants, setTenants] = useState<TenantOut[]>([]);
  const [filteredTenants, setFilteredTenants] = useState<TenantOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [approvalFilter, setApprovalFilter] = useState<string>("");

  useEffect(() => {
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
      return;
    }

    async function loadData() {
      try {
        const res = await platformTenantsRequest(100, 0);
        if (res.ok && res.data) {
          setTenants(res.data.items || []);
          setFilteredTenants(res.data.items || []);
        }
      } catch (err) {
        setError("Failed to load companies");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [hasRole, router]);

  // Filter tenants based on search and filters
  useEffect(() => {
    let filtered = tenants;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.code.toLowerCase().includes(query)
      );
    }

    if (statusFilter) {
      filtered = filtered.filter((t) =>
        statusFilter === "active" ? t.is_active : !t.is_active
      );
    }

    if (approvalFilter) {
      filtered = filtered.filter((t) => t.approval_status === approvalFilter);
    }

    setFilteredTenants(filtered);
  }, [tenants, searchQuery, statusFilter, approvalFilter]);

  if (!hasRole("platform_owner")) {
    return null;
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString();
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Companies</h1>
        <Button onClick={() => router.push("/platform/tenants/new")}>
          + Create Company
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <Input
          type="text"
          placeholder="Search companies..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full sm:w-64"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Suspended</option>
        </select>
        <select
          value={approvalFilter}
          onChange={(e) => setApprovalFilter(e.target.value)}
          className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Approvals</option>
          <option value="approved">Approved</option>
          <option value="pending">Pending</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-lg bg-slate-800/50 p-3">
          <p className="text-xs text-slate-400">Total</p>
          <p className="text-xl font-semibold text-slate-100">{tenants.length}</p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3">
          <p className="text-xs text-slate-400">Active</p>
          <p className="text-xl font-semibold text-emerald-400">
            {tenants.filter((t) => t.is_active).length}
          </p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3">
          <p className="text-xs text-slate-400">Pending</p>
          <p className="text-xl font-semibold text-amber-400">
            {tenants.filter((t) => t.approval_status === "pending").length}
          </p>
        </div>
        <div className="rounded-lg bg-slate-800/50 p-3">
          <p className="text-xs text-slate-400">Suspended</p>
          <p className="text-xl font-semibold text-rose-400">
            {tenants.filter((t) => !t.is_active).length}
          </p>
        </div>
      </div>

      {/* Companies Table */}
      <Card title={`Companies (${filteredTenants.length})`}>
        {loading ? (
          <div className="flex min-h-[30vh] items-center justify-center text-slate-400">
            Loading companies…
          </div>
        ) : (
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
                {filteredTenants.map((tenant) => (
                  <tr key={tenant.id} className="hover:bg-slate-800/30">
                    <td className="py-3 text-slate-200">{tenant.name}</td>
                    <td className="py-3 text-slate-400 font-mono text-xs">
                      {tenant.code}
                    </td>
                    <td className="py-3">
                      {tenant.is_active ? (
                        <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400">
                          Active
                        </span>
                      ) : (
                        <span className="inline-flex items-center rounded-full bg-rose-500/10 px-2 py-1 text-xs font-medium text-rose-400">
                          Suspended
                        </span>
                      )}
                    </td>
                    <td className="py-3">
                      <ApprovalBadge status={tenant.approval_status} />
                    </td>
                    <td className="py-3 text-slate-400">
                      {formatDate(tenant.created_at)}
                    </td>
                    <td className="py-3">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => router.push(`/platform/tenants/${tenant.id}`)}
                      >
                        Manage
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredTenants.length === 0 && (
              <p className="py-8 text-center text-slate-400">
                {tenants.length === 0
                  ? "No companies found"
                  : "No companies match the filters"}
              </p>
            )}
          </div>
        )}
      </Card>
    </div>
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
