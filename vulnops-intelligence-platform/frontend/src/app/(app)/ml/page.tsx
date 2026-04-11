"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getMlModelInfo } from "@/lib/api";
import type { MlModelInfoResponse } from "@/types/api";

export default function MlPage() {
  const [info, setInfo] = useState<MlModelInfoResponse | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const i = await getMlModelInfo();
      if (!cancelled) setInfo(i);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (info === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading model metadata…
      </p>
    );
  }

  if (!info) {
    return (
      <p className="text-rose-400" role="alert">
        Could not load model info. Check API and authentication.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">ML insights</h2>
        <p className="mt-1 text-slate-400">
          Server-side risk prioritization bundle status (see Phase 4 training).
        </p>
      </div>

      <Card title="Model status">
        <dl className="grid max-w-2xl grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm">
          <dt className="text-slate-500">Inference enabled</dt>
          <dd className="text-slate-200">{info.inference_enabled ? "Yes" : "No"}</dd>
          <dt className="text-slate-500">Model loaded</dt>
          <dd className="text-slate-200">{info.model_loaded ? "Yes" : "No"}</dd>
          <dt className="text-slate-500">Artifact path</dt>
          <dd className="break-all font-mono text-xs text-slate-400">{info.artifact_path || "—"}</dd>
          <dt className="text-slate-500">Name / version</dt>
          <dd className="text-slate-300">
            {info.model_name || "—"} {info.model_version ? `@ ${info.model_version}` : ""}
          </dd>
          <dt className="text-slate-500">Trained (UTC)</dt>
          <dd className="text-slate-300">{info.trained_at_utc || "—"}</dd>
          <dt className="text-slate-500">Training samples</dt>
          <dd className="text-slate-300">{info.n_samples ?? "—"}</dd>
        </dl>
        {info.metrics_holdout && Object.keys(info.metrics_holdout).length > 0 ? (
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-medium text-slate-300">Holdout metrics</h3>
            <pre className="max-h-48 overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400">
              {JSON.stringify(info.metrics_holdout, null, 2)}
            </pre>
          </div>
        ) : null}
      </Card>

      <p className="text-sm text-slate-500">
        Run predictions from any finding detail page using <strong className="text-slate-400">Predict urgency</strong>.
      </p>
    </div>
  );
}
