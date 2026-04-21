"use client";

import { useEffect } from "react";
import { Play, RefreshCw, Clock, CheckCircle, XCircle, Loader2, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { PageHeader } from "@/components/ui/PageHeader";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { useJobs } from "@/hooks/useJobs";

function formatDuration(createdAt: string, completedAt?: string | null, startedAt?: string | null): string {
  const start = startedAt ? new Date(startedAt).getTime() : new Date(createdAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const diffMs = end - start;
  
  if (diffMs < 1000) return "< 1s";
  if (diffMs < 60000) return `${Math.round(diffMs / 1000)}s`;
  if (diffMs < 3600000) return `${Math.round(diffMs / 60000)}m`;
  return `${Math.round(diffMs / 3600000)}h`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

export default function JobsPage() {
  const { jobs, loading, error, fetchJobs, enqueueJob } = useJobs();

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Background Jobs" description="Monitor and manage asynchronous processing tasks" />
        <ErrorState title="Failed to load jobs" message={error} onRetry={fetchJobs} />
      </div>
    );
  }

  const pendingCount = jobs.filter(j => j.status === "PENDING").length;
  const runningCount = jobs.filter(j => j.status === "RUNNING").length;
  const completedCount = jobs.filter(j => j.status === "COMPLETED").length;
  const failedCount = jobs.filter(j => j.status === "FAILED").length;

  return (
    <div className="space-y-6">
      <PageHeader title="Background Jobs" description="Monitor and manage asynchronous processing tasks" />

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card title="Pending" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <Clock className="w-5 h-5 text-amber-500" />
            <span className="text-2xl font-bold text-slate-100">{pendingCount}</span>
          </div>
        </Card>
        <Card title="Running" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
            <span className="text-2xl font-bold text-slate-100">{runningCount}</span>
          </div>
        </Card>
        <Card title="Completed" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-500" />
            <span className="text-2xl font-bold text-slate-100">{completedCount}</span>
          </div>
        </Card>
        <Card title="Failed" className="text-center">
          <div className="flex items-center justify-center gap-2">
            <XCircle className="w-5 h-5 text-red-500" />
            <span className="text-2xl font-bold text-slate-100">{failedCount}</span>
          </div>
        </Card>
      </div>

      {/* Action Bar */}
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => enqueueJob("model_retrain", { source: "frontend" })}
            disabled={loading}
            className="gap-2"
          >
            <Play className="w-4 h-4" />
            Retrain Model
          </Button>
          <Button
            variant="secondary"
            onClick={() => enqueueJob("risk_recalculate", { source: "frontend" })}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Recalculate Risk
          </Button>
        </div>
        <Button
          variant="ghost"
          onClick={() => fetchJobs()}
          disabled={loading}
          className="gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Jobs Table */}
      <Card title="Job History" className={loading ? "opacity-70" : ""}>
        {loading && !jobs.length ? (
          <div className="space-y-3">
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
            <div className="h-12 animate-pulse bg-slate-800/50 rounded" />
          </div>
        ) : jobs.length > 0 ? (
          <DataTable
            columns={[
              { key: "job_kind", header: "Job Type", sortable: true, cell: (row) => row.job_kind },
              { key: "status", header: "Status", sortable: true, cell: (row) => {
                const statusColors = {
                  PENDING: { bg: "bg-amber-500/20", text: "text-amber-400", icon: Clock },
                  RUNNING: { bg: "bg-sky-500/20", text: "text-sky-400", icon: Loader2 },
                  COMPLETED: { bg: "bg-emerald-500/20", text: "text-emerald-400", icon: CheckCircle },
                  FAILED: { bg: "bg-red-500/20", text: "text-red-400", icon: XCircle },
                };
                const config = statusColors[row.status];
                const Icon = config.icon;
                return (
                  <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
                    <Icon className={`w-3.5 h-3.5 ${row.status === "RUNNING" ? "animate-spin" : ""}`} />
                    {row.status}
                  </span>
                );
              }},
              { key: "created", header: "Created", sortable: true, cell: (row) => formatDate(row.created_at) },
              { key: "duration", header: "Duration", sortable: false, cell: (row) => 
                row.status === "RUNNING" ? "Running..." : formatDuration(row.created_at, row.completed_at, row.started_at)
              },
              { key: "error", header: "", sortable: false, cell: (row) => 
                row.error_message ? (
                  <span title={row.error_message} className="inline-flex items-center gap-1 text-red-400 text-sm">
                    <AlertCircle className="w-4 h-4" />
                    Error
                  </span>
                ) : null
              },
            ]}
            data={jobs.map(j => ({ ...j, id: j.id }))}
            keyExtractor={(row) => row.id}
            sortable
          />
        ) : (
          <EmptyState
            title="No jobs found"
            description="Queue background jobs to get started"
            icon={<Clock className="w-10 h-10" />}
          />
        )}
      </Card>
    </div>
  );
}
