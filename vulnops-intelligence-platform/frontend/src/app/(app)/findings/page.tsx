"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { listFindings } from "@/lib/api";
import type { FindingOut, Paginated } from "@/types/api";

const PAGE = 25;

const STATUSES = ["", "OPEN", "IN_PROGRESS", "REMEDIATED"];

export default function FindingsPage() {
  const [data, setData] = useState<Paginated<FindingOut> | null | undefined>(undefined);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [qDraft, setQDraft] = useState("");
  const [offset, setOffset] = useState(0);

  const load = useCallback(async () => {
    setData(undefined);
    const res = await listFindings({
      limit: PAGE,
      offset,
      status: status || undefined,
      q: q || undefined,
    });
    setData(res);
  }, [offset, status, q]);

  useEffect(() => {
    void load();
  }, [load]);

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    setOffset(0);
    setQ(qDraft.trim());
  }

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE < total;

  if (data === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading findings…
      </p>
    );
  }

  if (!data) {
    return (
      <p className="text-rose-400" role="alert">
        Failed to load findings.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Findings</h2>
        <p className="mt-1 text-slate-400">
          {total} total · showing {rows.length} from offset {offset}
        </p>
      </div>

      <Card title="Filters">
        <form
          className="flex flex-col gap-4 md:flex-row md:flex-wrap md:items-end"
          onSubmit={applySearch}
        >
          <div className="min-w-[200px]">
            <label htmlFor="status-filter" className="mb-1 block text-sm font-medium text-slate-300">
              Status
            </label>
            <select
              id="status-filter"
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-slate-100 focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
            >
              {STATUSES.map((s) => (
                <option key={s || "all"} value={s}>
                  {s || "All statuses"}
                </option>
              ))}
            </select>
          </div>
          <Input
            id="findings-q"
            label="Search (notes, CVE)"
            value={qDraft}
            onChange={(e) => setQDraft(e.target.value)}
            placeholder="CVE-2024 or keyword"
            className="min-w-[220px] flex-1"
          />
          <Button type="submit">Apply</Button>
        </form>
      </Card>

      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[640px] text-left text-sm">
          <caption className="sr-only">Findings list</caption>
          <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">
                CVE
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Status
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Discovered
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Priority
              </th>
              <th scope="col" className="px-4 py-3 font-medium">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {rows.map((f) => (
              <tr key={f.id} className="hover:bg-slate-900/40">
                <td className="px-4 py-3 font-mono text-sky-300">
                  {f.cve_id || "—"}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={f.status}>{f.status}</Badge>
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {new Date(f.discovered_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {f.internal_priority_score ?? "—"}
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/findings/${f.id}`}
                    className="text-sky-400 hover:underline focus:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? (
          <p className="p-6 text-center text-slate-500">No findings match filters.</p>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={!hasPrev}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE))}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          disabled={!hasNext}
          onClick={() => setOffset((o) => o + PAGE)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
