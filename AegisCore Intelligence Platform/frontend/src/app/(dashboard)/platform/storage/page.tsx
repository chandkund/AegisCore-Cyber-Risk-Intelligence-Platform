"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { platformStorageStatsRequest } from "@/lib/api";

interface TenantStorage {
  tenant_id: string;
  storage_bytes: number;
  file_count: number;
}

interface StorageStats {
  total_storage_bytes: number;
  total_files: number;
  tenants: TenantStorage[];
}

export default function PlatformStoragePage() {
  const { hasRole } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!hasRole("platform_owner")) {
      router.replace("/dashboard");
      return;
    }

    async function loadData() {
      try {
        const res = await platformStorageStatsRequest();
        if (res.ok && res.data) {
          setStats(res.data);
        }
      } catch (err) {
        setError("Failed to load storage statistics");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [hasRole, router]);

  if (!hasRole("platform_owner")) {
    return null;
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function formatNumber(num: number): string {
    return num.toLocaleString();
  }

  // Sort tenants by storage usage (highest first)
  const sortedTenants = stats?.tenants.sort((a, b) => b.storage_bytes - a.storage_bytes) || [];

  // Calculate percentages
  const totalBytes = stats?.total_storage_bytes || 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-100">Storage Overview</h1>
        <Button variant="secondary" onClick={() => router.push("/platform")}>
          Back to Platform
        </Button>
      </div>

      {error && (
        <div className="rounded-lg bg-rose-500/10 p-4 text-rose-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex min-h-[50vh] items-center justify-center text-slate-400">
          Loading storage data…
        </div>
      ) : stats ? (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg bg-slate-800/50 p-4">
              <p className="text-sm text-slate-400">Total Storage</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">
                {formatBytes(stats.total_storage_bytes)}
              </p>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-4">
              <p className="text-sm text-slate-400">Total Files</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">
                {formatNumber(stats.total_files)}
              </p>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-4">
              <p className="text-sm text-slate-400">Active Tenants</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">
                {formatNumber(stats.tenants.length)}
              </p>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-4">
              <p className="text-sm text-slate-400">Avg per Tenant</p>
              <p className="mt-1 text-2xl font-semibold text-slate-100">
                {stats.tenants.length > 0
                  ? formatBytes(stats.total_storage_bytes / stats.tenants.length)
                  : "0 B"}
              </p>
            </div>
          </div>

          {/* Storage by Tenant */}
          <Card title="Storage by Company">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-slate-700">
                  <tr>
                    <th className="pb-3 font-medium text-slate-400">Company ID</th>
                    <th className="pb-3 font-medium text-slate-400">Storage Used</th>
                    <th className="pb-3 font-medium text-slate-400">File Count</th>
                    <th className="pb-3 font-medium text-slate-400">Percentage</th>
                    <th className="pb-3 font-medium text-slate-400">Visual</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {sortedTenants.map((tenant) => {
                    const percentage = totalBytes > 0
                      ? (tenant.storage_bytes / totalBytes) * 100
                      : 0;
                    return (
                      <tr key={tenant.tenant_id}>
                        <td className="py-3 text-slate-300 font-mono text-xs">
                          {tenant.tenant_id.slice(0, 16)}…
                        </td>
                        <td className="py-3 text-slate-100 font-medium">
                          {formatBytes(tenant.storage_bytes)}
                        </td>
                        <td className="py-3 text-slate-400">
                          {formatNumber(tenant.file_count)}
                        </td>
                        <td className="py-3 text-slate-400">
                          {percentage.toFixed(1)}%
                        </td>
                        <td className="py-3">
                          <div className="h-2 w-32 rounded-full bg-slate-700">
                            <div
                              className="h-2 rounded-full bg-indigo-500"
                              style={{ width: `${Math.max(percentage, 1)}%` }}
                            />
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {sortedTenants.length === 0 && (
                <p className="py-8 text-center text-slate-400">
                  No storage data available
                </p>
              )}
            </div>
          </Card>

          {/* Storage Distribution Chart Info */}
          <Card title="Storage Distribution">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Top Consumers */}
              <div className="rounded-lg bg-slate-800/30 p-4">
                <h3 className="mb-3 text-sm font-medium text-slate-300">
                  Top 5 Storage Consumers
                </h3>
                <div className="space-y-2">
                  {sortedTenants.slice(0, 5).map((tenant, index) => (
                    <div key={tenant.tenant_id} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-4">{index + 1}</span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-400 font-mono">
                            {tenant.tenant_id.slice(0, 12)}…
                          </span>
                          <span className="text-xs text-slate-300">
                            {formatBytes(tenant.storage_bytes)}
                          </span>
                        </div>
                        <div className="mt-1 h-1.5 w-full rounded-full bg-slate-700">
                          <div
                            className="h-1.5 rounded-full bg-emerald-500"
                            style={{
                              width: `${Math.max(
                                (tenant.storage_bytes / (sortedTenants[0]?.storage_bytes || 1)) * 100,
                                1
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  {sortedTenants.length === 0 && (
                    <p className="text-sm text-slate-500">No data available</p>
                  )}
                </div>
              </div>

              {/* Storage Stats Summary */}
              <div className="rounded-lg bg-slate-800/30 p-4">
                <h3 className="mb-3 text-sm font-medium text-slate-300">Storage Statistics</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Companies with files:</span>
                    <span className="text-sm text-slate-200">
                      {stats.tenants.filter((t) => t.file_count > 0).length}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Largest single file:</span>
                    <span className="text-sm text-slate-200">-</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Average files per company:</span>
                    <span className="text-sm text-slate-200">
                      {stats.tenants.length > 0
                        ? Math.round(stats.total_files / stats.tenants.length)
                        : 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-slate-400">Storage efficiency:</span>
                    <span className="text-sm text-emerald-400">Good</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}
