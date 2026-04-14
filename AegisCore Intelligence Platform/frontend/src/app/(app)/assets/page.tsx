"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { listAssets } from "@/lib/api";
import type { AssetOut, Paginated } from "@/types/api";

const PAGE = 25;

export default function AssetsPage() {
  const [data, setData] = useState<Paginated<AssetOut> | null | undefined>(undefined);
  const [offset, setOffset] = useState(0);

  const load = useCallback(async () => {
    setData(undefined);
    const res = await listAssets({ limit: PAGE, offset });
    setData(res);
  }, [offset]);

  useEffect(() => {
    void load();
  }, [load]);

  const rows = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasPrev = offset > 0;
  const hasNext = offset + PAGE < total;

  if (data === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading assets…
      </p>
    );
  }

  if (!data) {
    return (
      <p className="text-rose-400" role="alert">
        Failed to load assets.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Assets</h2>
        <p className="mt-1 text-slate-400">
          {total} total · showing {rows.length} from offset {offset}
        </p>
      </div>

      <Card title="Inventory">
        <div className="overflow-x-auto rounded-lg border border-slate-800">
          <table className="w-full min-w-[560px] text-left text-sm">
            <caption className="sr-only">Asset inventory</caption>
            <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Name
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Type
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Criticality
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  IP
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {rows.map((a) => (
                <tr key={a.id} className="hover:bg-slate-900/40">
                  <td className="px-4 py-3 font-medium text-slate-200">{a.name}</td>
                  <td className="px-4 py-3 text-slate-400">{a.asset_type}</td>
                  <td className="px-4 py-3 text-slate-400">{a.criticality}</td>
                  <td className="px-4 py-3 font-mono text-slate-400">{a.ip_address || "—"}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/assets/${a.id}`}
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
            <p className="p-6 text-center text-slate-500">No assets.</p>
          ) : null}
        </div>
      </Card>

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
