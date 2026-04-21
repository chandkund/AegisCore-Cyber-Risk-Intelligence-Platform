"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Card } from "@/components/ui/Card";
import { KpiCard } from "@/components/ui/KpiCard";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyStateUpload } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { TopRisksWidget } from "@/components/prioritization/TopRisksWidget";
import {
  getAnalyticsSummary,
  getRiskTrend,
  getSlaForecast,
} from "@/lib/api";
import type {
  AnalyticsSummary,
  RiskTrendResponse,
  SlaForecastResponse,
} from "@/types/api";
import {
  Shield,
  AlertTriangle,
  AlertCircle,
  FileWarning,
  Activity,
  Upload,
} from "lucide-react";

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null | undefined>(
    undefined
  );
  const [trend, setTrend] = useState<RiskTrendResponse | null>(null);
  const [sla, setSla] = useState<SlaForecastResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const fetchData = async () => {
    setIsRetrying(true);
    setErr(null);
    try {
      const [s, t, f] = await Promise.all([
        getAnalyticsSummary(),
        getRiskTrend(14),
        getSlaForecast(),
      ]);
      setSummary(s ?? null);
      setTrend(t);
      setSla(f);
    } catch (error) {
      setErr(
        error instanceof Error ? error.message : "Failed to load dashboard data"
      );
    } finally {
      setIsRetrying(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Loading state
  if (summary === undefined && !err) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Security Dashboard"
          description="Real-time overview of your security posture"
        />
        {/* KPI Skeletons */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <KpiCard key={i} title="Loading..." value="-" loading />
          ))}
        </div>
        {/* Charts Skeletons */}
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Risk Trend" className="h-[320px]" />
          <Card title="Severity Distribution" className="h-[320px]" />
        </div>
      </div>
    );
  }

  // Error state
  if (err) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Security Dashboard"
          description="Real-time overview of your security posture"
        />
        <ErrorState
          title="Failed to load dashboard"
          message={err}
          onRetry={fetchData}
        />
      </div>
    );
  }

  // Empty state - no data uploaded yet
  const hasNoData =
    !summary ||
    (summary.total_open_findings === 0 &&
      (!summary.by_severity || summary.by_severity.length === 0));

  if (hasNoData) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Security Dashboard"
          description="Real-time overview of your security posture"
        />
        <EmptyStateUpload
          onUpload={() => (window.location.href = "/uploads")}
        />
      </div>
    );
  }

  // Calculate severity counts
  const severityCounts = {
    critical:
      summary?.by_severity?.find((s) => s.severity === "CRITICAL")?.count || 0,
    high:
      summary?.by_severity?.find((s) => s.severity === "HIGH")?.count || 0,
    medium:
      summary?.by_severity?.find((s) => s.severity === "MEDIUM")?.count || 0,
    low:
      summary?.by_severity?.find((s) => s.severity === "LOW")?.count || 0,
  };

  // Calculate trend direction
  const trendPoints = trend?.points || [];
  const recentTrend =
    trendPoints.length >= 2
      ? trendPoints[trendPoints.length - 1].opened_count -
        trendPoints[trendPoints.length - 2].opened_count
      : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Security Dashboard"
        description="Real-time overview of your security posture"
      >
        <Button
          variant="outline"
          size="sm"
          onClick={fetchData}
          disabled={isRetrying}
          className="gap-2"
        >
          <Activity className="h-4 w-4" />
          {isRetrying ? "Refreshing..." : "Refresh"}
        </Button>
        <Link href="/uploads">
          <Button size="sm" className="gap-2">
            <Upload className="h-4 w-4" />
            Upload Data
          </Button>
        </Link>
      </PageHeader>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          title="Total Findings"
          value={summary?.total_open_findings?.toLocaleString() || "0"}
          subtitle="Open vulnerabilities"
          icon={<Shield className="h-5 w-5" />}
          status="info"
          trend={
            recentTrend !== 0
              ? {
                  value: Math.abs(recentTrend),
                  label: recentTrend > 0 ? "vs yesterday" : "vs yesterday",
                  direction: recentTrend > 0 ? "up" : "down",
                }
              : undefined
          }
        />
        <KpiCard
          title="Critical Risk"
          value={severityCounts.critical.toLocaleString()}
          subtitle="Immediate attention required"
          icon={<AlertTriangle className="h-5 w-5" />}
          status={severityCounts.critical > 0 ? "error" : "success"}
        />
        <KpiCard
          title="High Risk"
          value={severityCounts.high.toLocaleString()}
          subtitle="Should be addressed soon"
          icon={<AlertCircle className="h-5 w-5" />}
          status={severityCounts.high > 0 ? "warning" : "success"}
        />
        <KpiCard
          title="Risk Score"
          value={trendPoints.length > 0 && trendPoints[trendPoints.length - 1].avg_risk_score
            ? trendPoints[trendPoints.length - 1].avg_risk_score!.toFixed(1)
            : "N/A"}
          subtitle="Average across all findings"
          icon={<FileWarning className="h-5 w-5" />}
          status="neutral"
        />
      </div>

      {/* Main Charts Section */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Risk Trend */}
        <Card title="Risk Trend (14 Days)" className="relative">
          {trend?.points && trend.points.length > 0 ? (
            <div className="space-y-3">
              {trend.points.slice(-7).map((point) => (
                <div
                  key={point.date}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-slate-400">{point.date}</span>
                  <div className="flex items-center gap-4">
                    <Badge variant="outline" className="font-mono">
                      +{point.opened_count} new
                    </Badge>
                    <span className="text-slate-300 w-16 text-right">
                      {point.avg_risk_score
                        ? point.avg_risk_score.toFixed(1)
                        : "—"}
                    </span>
                  </div>
                </div>
              ))}
              <div className="mt-4 border-t border-slate-700/50 pt-4">
                <Link
                  href="/analytics"
                  className="text-sm text-sky-400 hover:text-sky-300"
                >
                  View full analytics →
                </Link>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No trend data available. Upload findings to see trends.
            </p>
          )}
        </Card>

        {/* Severity Distribution */}
        <Card title="Severity Distribution" className="relative">
          <div className="space-y-3">
            {severityCounts.critical > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-red-500" />
                  <span className="text-sm text-slate-300">Critical</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 w-32 rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-red-500 transition-all"
                      style={{
                        width: `${(severityCounts.critical / (summary?.total_open_findings || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-mono text-slate-300">
                    {severityCounts.critical}
                  </span>
                </div>
              </div>
            )}
            {severityCounts.high > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-orange-500" />
                  <span className="text-sm text-slate-300">High</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 w-32 rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-orange-500 transition-all"
                      style={{
                        width: `${(severityCounts.high / (summary?.total_open_findings || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-mono text-slate-300">
                    {severityCounts.high}
                  </span>
                </div>
              </div>
            )}
            {severityCounts.medium > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-amber-500" />
                  <span className="text-sm text-slate-300">Medium</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 w-32 rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-amber-500 transition-all"
                      style={{
                        width: `${(severityCounts.medium / (summary?.total_open_findings || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-mono text-slate-300">
                    {severityCounts.medium}
                  </span>
                </div>
              </div>
            )}
            {severityCounts.low > 0 && (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-emerald-500" />
                  <span className="text-sm text-slate-300">Low</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 flex-1 w-32 rounded-full bg-slate-700">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all"
                      style={{
                        width: `${(severityCounts.low / (summary?.total_open_findings || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-8 text-right text-sm font-mono text-slate-300">
                    {severityCounts.low}
                  </span>
                </div>
              </div>
            )}
            {summary?.total_open_findings === 0 && (
              <p className="text-sm text-slate-500">No open findings</p>
            )}
          </div>
        </Card>
      </div>

      {/* SLA Forecast */}
      {sla && (
        <Card title="SLA Forecast" className="relative">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <p className="text-xs text-slate-500">Due Next 7 Days</p>
              <p className="text-2xl font-semibold text-slate-200">
                {sla.due_next_7_days}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-slate-500">Due Next 14 Days</p>
              <p className="text-2xl font-semibold text-slate-200">
                {sla.due_next_14_days}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-slate-500">Predicted Breaches (7d)</p>
              <p
                className={`text-2xl font-semibold ${
                  (sla.predicted_breaches_next_7_days || 0) > 0
                    ? "text-amber-400"
                    : "text-emerald-400"
                }`}
              >
                {sla.predicted_breaches_next_7_days || 0}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs text-slate-500">Predicted Breaches (14d)</p>
              <p
                className={`text-2xl font-semibold ${
                  (sla.predicted_breaches_next_14_days || 0) > 0
                    ? "text-rose-400"
                    : "text-emerald-400"
                }`}
              >
                {sla.predicted_breaches_next_14_days || 0}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Top Risks Widget */}
      <TopRisksWidget />

      {/* Assistant Panel */}
      <AssistantPanel />
    </div>
  );
}
