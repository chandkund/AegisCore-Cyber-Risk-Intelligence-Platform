"use client";

import { useEffect } from "react";
import { AlertTriangle, CheckCircle, Clock, FileText, TrendingUp, XCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { KpiCard } from "@/components/ui/KpiCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { useCompliance } from "@/hooks/useCompliance";

export default function CompliancePage() {
  const { report, clusters, loading, error, loadAll } = useCompliance();

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Compliance & Governance" description="Track SLA performance, overdue findings, and compliance metrics" />
        <ErrorState title="Failed to load compliance data" message={error} onRetry={loadAll} />
      </div>
    );
  }

  if (!loading && !report) {
    return (
      <div className="space-y-6">
        <PageHeader title="Compliance & Governance" description="Track SLA performance, overdue findings, and compliance metrics" />
        <EmptyState
          title="No compliance data available"
          description="Upload vulnerability data to see compliance metrics"
          icon={<FileText className="w-10 h-10" />}
          action={{ label: "Upload Data", onClick: () => window.location.href = "/uploads" }}
        />
      </div>
    );
  }

  const breachRate = report?.sla_breach_rate ? Math.round(report.sla_breach_rate * 100) : 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Compliance & Governance" description="Track SLA performance, overdue findings, and compliance metrics" />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Open Findings"
          value={report?.open_findings ?? 0}
          icon={<FileText className="w-5 h-5" />}
          trend={report && report.open_findings > 0 ? { value: report.open_findings, label: "pending review", direction: "neutral" } : undefined}
          status="neutral"
          loading={loading}
        />
        <KpiCard
          title="Overdue"
          value={report?.overdue_findings ?? 0}
          icon={<AlertTriangle className="w-5 h-5" />}
          status={report && report.overdue_findings > 0 ? "warning" : "neutral"}
          trend={report && report.overdue_findings > 0 ? { value: report.overdue_findings, label: "need attention", direction: "up" } : undefined}
          loading={loading}
        />
        <KpiCard
          title="SLA Breach Rate"
          value={`${breachRate}%`}
          icon={breachRate > 10 ? <XCircle className="w-5 h-5" /> : <CheckCircle className="w-5 h-5" />}
          status={breachRate > 10 ? "error" : breachRate > 5 ? "warning" : "success"}
          trend={breachRate > 0 ? { value: breachRate, label: "of total findings", direction: breachRate < 5 ? "down" : "up" } : undefined}
          loading={loading}
        />
        <KpiCard
          title="Avg Time to Remediate"
          value={report?.mean_time_to_remediate_days ? `${report.mean_time_to_remediate_days}d` : "N/A"}
          icon={<Clock className="w-5 h-5" />}
          status="neutral"
          trend={report?.mean_time_to_remediate_days ? { value: report.mean_time_to_remediate_days, label: "days average", direction: "neutral" } : undefined}
          loading={loading}
        />
      </div>

      {/* Findings by Status and Severity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Findings by Severity" className={loading ? "opacity-70" : ""}>
          {loading ? (
            <div className="h-32 animate-pulse bg-slate-800/50 rounded" />
          ) : (
            <div className="space-y-3">
              {Object.entries(report?.findings_by_severity ?? {}).sort((a, b) => b[1] - a[1]).map(([severity, count]) => (
                <div key={severity} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge
                      tone={severity}
                    >
                      {severity}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 flex-1 ml-4">
                    <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          severity === "CRITICAL" ? "bg-red-500" :
                          severity === "HIGH" ? "bg-orange-500" :
                          severity === "MEDIUM" ? "bg-amber-500" : "bg-slate-500"
                        }`}
                        style={{ width: `${Math.min(100, (count / (report?.total_findings || 1)) * 100)}%` }}
                      />
                    </div>
                    <span className="text-slate-300 w-12 text-right">{count}</span>
                  </div>
                </div>
              ))}
              {Object.keys(report?.findings_by_severity ?? {}).length === 0 && (
                <div className="text-slate-500 text-sm">No findings data available</div>
              )}
            </div>
          )}
        </Card>

        <Card title="Findings by Status" className={loading ? "opacity-70" : ""}>
          {loading ? (
            <div className="h-32 animate-pulse bg-slate-800/50 rounded" />
          ) : (
            <div className="space-y-3">
              {Object.entries(report?.findings_by_status ?? {}).sort((a, b) => b[1] - a[1]).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <Badge
                    tone={status === "OPEN" ? "OPEN" : status === "IN_PROGRESS" ? "IN_PROGRESS" : status === "RESOLVED" ? "REMEDIATED" : "INFO"}
                  >
                    {status}
                  </Badge>
                  <div className="flex items-center gap-4 flex-1 ml-4">
                    <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          status === "OPEN" ? "bg-amber-500" :
                          status === "IN_PROGRESS" ? "bg-sky-500" :
                          status === "RESOLVED" ? "bg-emerald-500" : "bg-slate-500"
                        }`}
                        style={{ width: `${Math.min(100, (count / (report?.total_findings || 1)) * 100)}%` }}
                      />
                    </div>
                    <span className="text-slate-300 w-12 text-right">{count}</span>
                  </div>
                </div>
              ))}
              {Object.keys(report?.findings_by_status ?? {}).length === 0 && (
                <div className="text-slate-500 text-sm">No status data available</div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Root Cause Clusters */}
      <Card title="Root Cause Clusters" className={loading ? "opacity-70" : ""}>
        {loading ? (
          <div className="h-48 animate-pulse bg-slate-800/50 rounded" />
        ) : clusters.length > 0 ? (
          <DataTable
            columns={[
              { key: "category", header: "Category", sortable: true, cell: (row) => row.category },
              { key: "count", header: "Count", sortable: true, cell: (row) => row.count },
              { key: "percentage", header: "% of Total", sortable: true, cell: (row) => row.percentage },
              { key: "examples", header: "Example CVEs", sortable: false, cell: (row) => row.examples },
            ]}
            data={clusters.map(c => ({
              id: c.root_cause_category,
              category: c.root_cause_category,
              count: c.count,
              percentage: `${c.percentage.toFixed(1)}%`,
              examples: c.example_cves.slice(0, 3).join(", ") || "N/A",
            }))}
            keyExtractor={(row) => row.id}
            sortable
          />
        ) : (
          <EmptyState
            title="No root cause data"
            description="Root cause clusters will appear when findings are analyzed"
            icon={<TrendingUp className="w-8 h-8" />}
          />
        )}
      </Card>
    </div>
  );
}
