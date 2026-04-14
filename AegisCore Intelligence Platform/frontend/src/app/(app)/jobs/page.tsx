"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { enqueueJob, listJobs } from "@/lib/api";
import type { JobOut } from "@/types/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setJobs((await listJobs(100)) ?? []);
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function queue(kind: string) {
    setBusy(true);
    await enqueueJob(kind, { source: "frontend" });
    setBusy(false);
    await refresh();
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-100">Background jobs</h2>
      <Card title="Queue jobs">
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" onClick={() => void queue("model_retrain")} disabled={busy}>
            Queue model retrain
          </Button>
          <Button type="button" variant="secondary" onClick={() => void queue("risk_recalculate")} disabled={busy}>
            Queue risk recalc
          </Button>
        </div>
      </Card>
      <Card title="Recent jobs">
        <ul className="space-y-2 text-sm">
          {jobs.map((j) => (
            <li key={j.id} className="rounded border border-slate-800 p-2 text-slate-300">
              <span className="font-medium text-slate-100">{j.job_kind}</span> · {j.status}
            </li>
          ))}
          {!jobs.length ? <li className="text-slate-500">No jobs queued.</li> : null}
        </ul>
      </Card>
    </div>
  );
}
