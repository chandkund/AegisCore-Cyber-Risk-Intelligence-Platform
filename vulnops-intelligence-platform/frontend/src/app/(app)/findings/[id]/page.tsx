"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  getAsset,
  getCveRecord,
  getFinding,
  predictFinding,
} from "@/lib/api";
import type { AssetOut, CveRecordOut, FindingOut, MlPredictionResponse } from "@/types/api";

export default function FindingDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const [finding, setFinding] = useState<FindingOut | null | undefined>(undefined);
  const [cve, setCve] = useState<CveRecordOut | null>(null);
  const [asset, setAsset] = useState<AssetOut | null>(null);
  const [pred, setPred] = useState<MlPredictionResponse | null>(null);
  const [predErr, setPredErr] = useState<string | null>(null);
  const [predLoading, setPredLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      const f = await getFinding(id);
      if (cancelled) return;
      setFinding(f);
      if (!f) return;
      const [c, a] = await Promise.all([
        getCveRecord(f.cve_record_id),
        getAsset(f.asset_id),
      ]);
      if (!cancelled) {
        setCve(c);
        setAsset(a);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  async function runPredict() {
    if (!id) return;
    setPred(null);
    setPredErr(null);
    setPredLoading(true);
    const r = await predictFinding(id);
    setPredLoading(false);
    if (!r.ok) {
      setPredErr(r.error);
      return;
    }
    setPred(r.data);
  }

  if (finding === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading finding…
      </p>
    );
  }

  if (!finding) {
    return (
      <p className="text-rose-400" role="alert">
        Finding not found.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/findings" className="text-sm text-sky-400 hover:underline">
          ← Findings
        </Link>
        <h2 className="mt-2 text-2xl font-bold text-slate-100">
          {finding.cve_id || "Finding"} · <Badge tone={finding.status}>{finding.status}</Badge>
        </h2>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Record">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-slate-500">ID</dt>
            <dd className="font-mono text-slate-300">{finding.id}</dd>
            <dt className="text-slate-500">Asset</dt>
            <dd>
              {asset ? (
                <Link href={`/assets/${asset.id}`} className="text-sky-400 hover:underline">
                  {asset.name}
                </Link>
              ) : (
                <span className="text-slate-400">{finding.asset_id}</span>
              )}
            </dd>
            <dt className="text-slate-500">Discovered</dt>
            <dd className="text-slate-300">
              {new Date(finding.discovered_at).toLocaleString()}
            </dd>
            <dt className="text-slate-500">Due</dt>
            <dd className="text-slate-300">
              {finding.due_at ? new Date(finding.due_at).toLocaleString() : "—"}
            </dd>
            <dt className="text-slate-500">Priority score</dt>
            <dd className="text-slate-300">{finding.internal_priority_score ?? "—"}</dd>
            <dt className="text-slate-500">Notes</dt>
            <dd className="text-slate-300">{finding.notes || "—"}</dd>
          </dl>
        </Card>

        <Card title="CVE">
          {cve ? (
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-slate-500">Severity</dt>
                <dd className="mt-1">
                  <Badge tone={cve.severity}>{cve.severity}</Badge>
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">CVSS</dt>
                <dd className="text-slate-300">{cve.cvss_base_score ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Title</dt>
                <dd className="text-slate-300">{cve.title || "—"}</dd>
              </div>
              <div>
                <dt className="text-slate-500">Exploit known</dt>
                <dd className="text-slate-300">{cve.exploit_available ? "Yes" : "No"}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-slate-500">CVE metadata unavailable.</p>
          )}
        </Card>
      </div>

      <Card title="ML prioritization">
        <p className="mb-3 text-sm text-slate-400">
          Runs <code className="text-sky-400">POST /api/v1/ml/predict/finding/{"{id}"}</code> for this row.
        </p>
        <Button type="button" onClick={() => void runPredict()} disabled={predLoading}>
          {predLoading ? "Scoring…" : "Predict urgency"}
        </Button>
        {predErr ? (
          <p className="mt-3 text-sm text-rose-400" role="alert">
            {predErr}
          </p>
        ) : null}
        {pred ? (
          <div className="mt-4 space-y-2 text-sm">
            <p>
              <span className="text-slate-500">Probability urgent: </span>
              <span className="font-mono text-sky-300">
                {(pred.probability_urgent * 100).toFixed(1)}%
              </span>
            </p>
            <p className="text-slate-500">Reference time: {pred.reference_time_utc}</p>
            <div>
              <p className="mb-1 font-medium text-slate-300">Explanation (feature direction)</p>
              <ul className="max-h-40 overflow-auto rounded border border-slate-800 font-mono text-xs">
                {pred.explain.map((e) => (
                  <li key={e.name} className="flex justify-between gap-2 border-b border-slate-800/80 px-2 py-1 last:border-0">
                    <span className="text-slate-400">{e.name}</span>
                    <span className="text-slate-200">{e.value.toFixed(4)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
