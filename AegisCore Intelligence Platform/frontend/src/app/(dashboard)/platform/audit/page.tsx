"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  platformAuditLogsRequest,
  platformAuditLogsSummaryRequest,
} from "@/lib/api";

interface AuditLog {
  id: string;
  tenant_id: string | null;
  tenant_name: string | null;
  actor_user_id: string | null;
  actor_email: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  payload: object | null;
  occurred_at: string;
}

interface AuditSummary {
  period_days: number;
  total_actions: number;
  actions_by_type: Array<{ action: string; count: number }>;
  actions_by_tenant: Array<{ tenant_id: string; count: number }>;
  daily_trend: Array<{ date: string; count: number }>;
}

export default function PlatformAuditPage() {
  const { hasRole } = useAuth();
  const router = useRouter();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [periodDays, setPeriodDays] = useState(7);
  const [actionFilter, setActionFilter] = useState<string>("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>("");

  useEffect(() => {
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
      return;
    }

    async function loadData() {
      try {
        setLoading(true);
        const [logsRes, summaryRes] = await Promise.all([
          platformAuditLogsRequest(50, 0, {
            action: actionFilter || undefined,
            resource_type: resourceTypeFilter || undefined,
          }),
          platformAuditLogsSummaryRequest(periodDays),
        ]);

        if (logsRes.ok && logsRes.data) {
          setLogs(logsRes.data.items);
        }
        if (summaryRes.ok && summaryRes.data) {
          setSummary(summaryRes.data);
        }
      } catch (err) {
        setError("Failed to load audit logs");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [hasRole, router, periodDays, actionFilter, resourceTypeFilter]);

  if (!hasRole("platform_owner")) {
    return null;
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleString();
  }

  function getActionBadgeColor(action: string): string {
    const colors: Record<string, string> = {
      FILE_UPLOAD: "bg-blue-500/10 text-blue-400",
      FILE_DELETE: "bg-rose-500/10 text-rose-400",
      LOGIN: "bg-emerald-500/10 text-emerald-400",
      LOGOUT: "bg-slate-500/10 text-slate-400",
      PASSWORD_RESET: "bg-amber-500/10 text-amber-400",
      TENANT_CREATE: "bg-indigo-500/10 text-indigo-400",
      TENANT_UPDATE: "bg-purple-500/10 text-purple-400",
    };
    return colors[action] || "bg-slate-500/10 text-slate-400";
  }

  function truncateId(id: string | null): string {
    if (!id) return "-";
    return id.slice(0, 8) + "…";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Audit Logs</h1>
        <Button variant="secondary" onClick={() => router.push("/platform")}>
          Back to Platform
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={periodDays}
          onChange={(e) => setPeriodDays(Number(e.target.value))}
          className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
        >
          <option value={7}>Last 7 days</option>
          <option value={14}>Last 14 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Actions</option>
          <option value="FILE_UPLOAD">File Upload</option>
          <option value="FILE_DELETE">File Delete</option>
          <option value="LOGIN">Login</option>
          <option value="LOGOUT">Logout</option>
          <option value="TENANT_CREATE">Tenant Create</option>
          <option value="TENANT_UPDATE">Tenant Update</option>
          <option value="PASSWORD_RESET">Password Reset</option>
        </select>
        <select
          value={resourceTypeFilter}
          onChange={(e) => setResourceTypeFilter(e.target.value)}
          className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-200"
        >
          <option value="">All Resource Types</option>
          <option value="upload">Upload</option>
          <option value="tenant">Tenant</option>
          <option value="user">User</option>
          <option value="asset">Asset</option>
        </select>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Total Actions</p>
            <p className="mt-1 text-2xl font-semibold text-slate-100">
              {summary.total_actions.toLocaleString()}
            </p>
            <p className="text-xs text-slate-500">Last {summary.period_days} days</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Unique Actions</p>
            <p className="mt-1 text-2xl font-semibold text-slate-100">
              {summary.actions_by_type.length}
            </p>
            <p className="text-xs text-slate-500">Different types</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Active Tenants</p>
            <p className="mt-1 text-2xl font-semibold text-slate-100">
              {summary.actions_by_tenant.filter((t) => t.count > 0).length}
            </p>
            <p className="text-xs text-slate-500">With activity</p>
          </div>
          <div className="rounded-lg bg-slate-800/50 p-4">
            <p className="text-sm text-slate-400">Daily Average</p>
            <p className="mt-1 text-2xl font-semibold text-slate-100">
              {summary.period_days > 0
                ? Math.round(summary.total_actions / summary.period_days)
                : 0}
            </p>
            <p className="text-xs text-slate-500">Actions per day</p>
          </div>
        </div>
      )}

      {/* Action Types Breakdown */}
      {summary && summary.actions_by_type.length > 0 && (
        <Card title="Actions by Type">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {summary.actions_by_type
              .sort((a, b) => b.count - a.count)
              .map((action) => (
                <div key={action.action} className="rounded-lg bg-slate-800/30 p-3">
                  <p className="text-xs text-slate-400">{action.action}</p>
                  <p className="text-lg font-semibold text-slate-100">
                    {action.count.toLocaleString()}
                  </p>
                </div>
              ))}
          </div>
        </Card>
      )}

      {/* Audit Logs Table */}
      <Card title="Recent Activity">
        {loading ? (
          <div className="flex min-h-[30vh] items-center justify-center text-slate-400">
            Loading audit logs…
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-slate-700">
                <tr>
                  <th className="pb-3 font-medium text-slate-400">Time</th>
                  <th className="pb-3 font-medium text-slate-400">Action</th>
                  <th className="pb-3 font-medium text-slate-400">Actor</th>
                  <th className="pb-3 font-medium text-slate-400">Company</th>
                  <th className="pb-3 font-medium text-slate-400">Resource</th>
                  <th className="pb-3 font-medium text-slate-400">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="py-3 text-slate-400 text-xs">
                      {formatDate(log.occurred_at)}
                    </td>
                    <td className="py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${getActionBadgeColor(
                          log.action
                        )}`}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td className="py-3 text-slate-300 text-xs">
                      {log.actor_email || truncateId(log.actor_user_id)}
                    </td>
                    <td className="py-3 text-slate-400 text-xs">
                      {log.tenant_name || truncateId(log.tenant_id)}
                    </td>
                    <td className="py-3 text-slate-400 text-xs">
                      {log.resource_type}:{truncateId(log.resource_id)}
                    </td>
                    <td className="py-3 text-slate-400 text-xs">
                      {log.payload && (
                        <button
                          onClick={() => alert(JSON.stringify(log.payload, null, 2))}
                          className="text-indigo-400 hover:text-indigo-300"
                        >
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {logs.length === 0 && (
              <p className="py-8 text-center text-slate-400">No audit logs found</p>
            )}
          </div>
        )}
      </Card>

      {/* Daily Trend */}
      {summary && summary.daily_trend.length > 0 && (
        <Card title="Activity Trend">
          <div className="space-y-2">
            {summary.daily_trend.slice(-14).map((day) => (
              <div key={day.date} className="flex items-center gap-3">
                <span className="text-xs text-slate-400 w-24">
                  {new Date(day.date).toLocaleDateString()}
                </span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="h-4 rounded bg-indigo-500/20 flex-1">
                      <div
                        className="h-4 rounded bg-indigo-500"
                        style={{
                          width: `${Math.max(
                            (day.count / (Math.max(...summary.daily_trend.map((d) => d.count)) || 1)) * 100,
                            1
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-slate-300 w-8">{day.count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
