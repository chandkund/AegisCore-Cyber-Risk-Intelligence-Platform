"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getComplianceReport, getRootCauseClusters, getSecretProviderStatus } from "@/lib/api";
import type { ComplianceReportOut, RootCauseCluster, SecretProviderStatus } from "@/types/api";

export default function CompliancePage() {
  const [report, setReport] = useState<ComplianceReportOut | null>(null);
  const [clusters, setClusters] = useState<RootCauseCluster[]>([]);
  const [secrets, setSecrets] = useState<SecretProviderStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [r, c, s] = await Promise.all([
        getComplianceReport(),
        getRootCauseClusters(10),
        getSecretProviderStatus(),
      ]);
      if (cancelled) return;
      setReport(r);
      setClusters(c ?? []);
      setSecrets(s);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-100">Compliance & Governance</h2>
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Open findings">
          <p className="text-3xl font-semibold text-slate-100">{report?.total_open ?? "—"}</p>
        </Card>
        <Card title="Overdue findings">
          <p className="text-3xl font-semibold text-amber-300">{report?.overdue_count ?? "—"}</p>
        </Card>
        <Card title="SLA breach rate">
          <p className="text-3xl font-semibold text-rose-300">
            {report ? `${(report.sla_breach_rate * 100).toFixed(1)}%` : "—"}
          </p>
        </Card>
      </div>
      <Card title="Root-cause clusters">
        <ul className="space-y-2 text-sm">
          {clusters.map((c) => (
            <li key={c.cluster_key} className="rounded border border-slate-800 p-2 text-slate-300">
              <span className="font-medium text-slate-100">{c.cluster_key}</span> · {c.finding_count} findings
            </li>
          ))}
          {!clusters.length ? <li className="text-slate-500">No clusters found.</li> : null}
        </ul>
      </Card>
      <Card title="Secrets provider">
        <p className="text-sm text-slate-300">
          Provider: <span className="font-medium text-slate-100">{secrets?.provider ?? "unknown"}</span> · configured:{" "}
          <span className="font-medium text-slate-100">{secrets?.configured ? "yes" : "no"}</span>
        </p>
      </Card>
    </div>
  );
}
