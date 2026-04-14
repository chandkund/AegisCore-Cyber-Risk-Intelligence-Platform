"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Card } from "@/components/ui/Card";
import { TopRisksWidget } from "@/components/prioritization/TopRisksWidget";
import { getAnalyticsSummary, getRiskTrend, getSlaForecast } from "@/lib/api";
import type { AnalyticsSummary, RiskTrendResponse, SlaForecastResponse } from "@/types/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null | undefined>(undefined);
  const [trend, setTrend] = useState<RiskTrendResponse | null>(null);
  const [sla, setSla] = useState<SlaForecastResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [s, t, f] = await Promise.all([getAnalyticsSummary(), getRiskTrend(14), getSlaForecast()]);
      if (!cancelled) {
        if (!s) setErr("Could not load analytics summary.");
        setSummary(s ?? null);
        setTrend(t);
        setSla(f);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (summary === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading dashboard…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Dashboard</h2>
        <p className="mt-1 text-slate-400">Open findings and distribution at a glance.</p>
      </div>
      {err ? (
        <p className="text-rose-400" role="alert">
          {err}
        </p>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card title="Open findings">
          <p className="text-3xl font-semibold text-sky-400">
            {summary?.total_open_findings ?? "—"}
          </p>
          <Link
            href="/findings"
            className="mt-2 inline-block text-sm text-sky-400 hover:underline focus:underline"
          >
            View findings
          </Link>
        </Card>
        <Card title="By severity (open)">
          <ul className="space-y-1 text-sm">
            {(summary?.by_severity ?? []).map((row) => (
              <li key={row.severity} className="flex justify-between gap-2">
                <span className="text-slate-300">{row.severity}</span>
                <span className="font-mono text-slate-400">{row.count}</span>
              </li>
            ))}
            {!summary?.by_severity?.length ? (
              <li className="text-slate-500">No data</li>
            ) : null}
          </ul>
        </Card>
        <Card title="By status">
          <ul className="space-y-1 text-sm">
            {(summary?.by_status ?? []).map((row) => (
              <li key={row.status} className="flex justify-between gap-2">
                <span className="text-slate-300">{row.status}</span>
                <span className="font-mono text-slate-400">{row.count}</span>
              </li>
            ))}
            {!summary?.by_status?.length ? (
              <li className="text-slate-500">No data</li>
            ) : null}
          </ul>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Risk trend (14d)">
          <div className="space-y-1 text-sm">
            {(trend?.points ?? []).slice(-5).map((p) => (
              <div key={p.date} className="flex justify-between text-slate-300">
                <span>{p.date}</span>
                <span className="font-mono">
                  +{p.opened_count} / avg {p.avg_risk_score ? p.avg_risk_score.toFixed(1) : "—"}
                </span>
              </div>
            ))}
            {!trend?.points?.length ? <p className="text-slate-500">No trend points yet.</p> : null}
          </div>
        </Card>
        <Card title="SLA forecast">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <p className="text-slate-300">
              Due next 7d: <span className="font-mono text-slate-100">{sla?.due_next_7_days ?? "—"}</span>
            </p>
            <p className="text-slate-300">
              Due next 14d: <span className="font-mono text-slate-100">{sla?.due_next_14_days ?? "—"}</span>
            </p>
            <p className="text-slate-300">
              Breaches (7d):{" "}
              <span className="font-mono text-amber-300">{sla?.predicted_breaches_next_7_days ?? "—"}</span>
            </p>
            <p className="text-slate-300">
              Breaches (14d):{" "}
              <span className="font-mono text-rose-300">{sla?.predicted_breaches_next_14_days ?? "—"}</span>
            </p>
          </div>
        </Card>
      </div>

      {/* Top Risks Widget */}
      <div className="mt-6">
        <TopRisksWidget />
      </div>
      <AssistantPanel />
      <div className="flex flex-wrap gap-3 text-sm">
        <Link href="/analytics" className="text-sky-400 hover:underline">
          Full analytics
        </Link>
        <Link href="/ml" className="text-sky-400 hover:underline">
          ML model status
        </Link>
      </div>
    </div>
  );
}
