"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/ui/Card";
import {
  getAnalyticsSummary,
  getBusinessUnitRisk,
  getTopAssets,
} from "@/lib/api";
import type {
  AnalyticsSummary,
  BusinessUnitRiskRow,
  TopAssetRow,
} from "@/types/api";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null | undefined>(undefined);
  const [top, setTop] = useState<TopAssetRow[] | null | undefined>(undefined);
  const [bu, setBu] = useState<BusinessUnitRiskRow[] | null | undefined>(undefined);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [s, t, b] = await Promise.all([
        getAnalyticsSummary(),
        getTopAssets(),
        getBusinessUnitRisk(),
      ]);
      if (cancelled) return;
      if (!s || !t || !b) setErr("One or more analytics endpoints failed.");
      setSummary(s);
      setTop(t);
      setBu(b);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const statusData = useMemo(
    () =>
      (summary?.by_status ?? []).map((r) => ({
        name: r.status,
        count: r.count,
      })),
    [summary]
  );
  const sevData = useMemo(
    () =>
      (summary?.by_severity ?? []).map((r) => ({
        name: r.severity,
        count: r.count,
      })),
    [summary]
  );

  const loading =
    summary === undefined || top === undefined || bu === undefined;

  if (loading) {
    return (
      <p className="text-slate-500" role="status">
        Loading analytics…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Analytics</h2>
        <p className="mt-1 text-slate-400">
          Summary distributions and top exposed assets (open findings).
        </p>
      </div>
      {err ? (
        <p className="text-amber-400" role="status">
          {err}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Findings by status">
          <div className="h-64" role="img" aria-label="Bar chart of findings by status">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="count" fill="#38bdf8" name="Count" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Open findings by severity">
          <div className="h-64" role="img" aria-label="Bar chart of open findings by severity">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sevData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0f172a",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="count" fill="#a78bfa" name="Count" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Top assets by open findings">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <caption className="sr-only">Assets ranked by open finding count</caption>
            <thead className="border-b border-slate-800 text-slate-400">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">
                  Asset
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Open
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Max CVSS
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {(top ?? []).map((r) => (
                <tr key={r.asset_id}>
                  <td className="px-3 py-2 text-slate-200">{r.asset_name}</td>
                  <td className="px-3 py-2 font-mono text-slate-400">{r.open_findings}</td>
                  <td className="px-3 py-2 font-mono text-slate-400">
                    {r.max_cvss != null ? Number(r.max_cvss).toFixed(1) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!top?.length ? (
            <p className="p-4 text-center text-slate-500">No rows.</p>
          ) : null}
        </div>
      </Card>

      <Card title="Risk by business unit">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <caption className="sr-only">Open and critical or high counts by business unit</caption>
            <thead className="border-b border-slate-800 text-slate-400">
              <tr>
                <th scope="col" className="px-3 py-2 font-medium">
                  Unit
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Open
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Critical / High
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {(bu ?? []).map((r) => (
                <tr key={r.business_unit_id}>
                  <td className="px-3 py-2 text-slate-200">
                    {r.business_unit_name}{" "}
                    <span className="text-slate-500">({r.business_unit_code})</span>
                  </td>
                  <td className="px-3 py-2 font-mono text-slate-400">{r.open_findings}</td>
                  <td className="px-3 py-2 font-mono text-slate-400">{r.critical_or_high}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!bu?.length ? (
            <p className="p-4 text-center text-slate-500">No rows.</p>
          ) : null}
        </div>
      </Card>
    </div>
  );
}
