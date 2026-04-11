"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getAnalyticsSummary } from "@/lib/api";
import type { AnalyticsSummary } from "@/types/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null | undefined>(undefined);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const s = await getAnalyticsSummary();
      if (!cancelled) {
        if (!s) setErr("Could not load analytics summary.");
        setSummary(s ?? null);
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
