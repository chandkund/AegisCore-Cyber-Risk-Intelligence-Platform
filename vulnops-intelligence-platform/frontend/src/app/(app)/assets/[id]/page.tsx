"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/Card";
import { getAsset } from "@/lib/api";
import type { AssetOut } from "@/types/api";

export default function AssetDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : "";
  const [asset, setAsset] = useState<AssetOut | null | undefined>(undefined);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      const a = await getAsset(id);
      if (!cancelled) setAsset(a);
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (asset === undefined) {
    return (
      <p className="text-slate-500" role="status">
        Loading asset…
      </p>
    );
  }

  if (!asset) {
    return (
      <p className="text-rose-400" role="alert">
        Asset not found.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link href="/assets" className="text-sm text-sky-400 hover:underline">
          ← Assets
        </Link>
        <h2 className="mt-2 text-2xl font-bold text-slate-100">{asset.name}</h2>
        <p className="mt-1 text-slate-400">{asset.asset_type}</p>
      </div>

      <Card title="Details">
        <dl className="grid max-w-xl grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-slate-500">ID</dt>
          <dd className="font-mono text-slate-300">{asset.id}</dd>
          <dt className="text-slate-500">Hostname</dt>
          <dd className="text-slate-300">{asset.hostname || "—"}</dd>
          <dt className="text-slate-500">IP</dt>
          <dd className="font-mono text-slate-300">{asset.ip_address || "—"}</dd>
          <dt className="text-slate-500">Criticality</dt>
          <dd className="text-slate-300">{asset.criticality}</dd>
          <dt className="text-slate-500">Owner</dt>
          <dd className="text-slate-300">{asset.owner_email || "—"}</dd>
          <dt className="text-slate-500">Active</dt>
          <dd className="text-slate-300">{asset.is_active ? "Yes" : "No"}</dd>
        </dl>
        <p className="mt-4 text-sm text-slate-500">
          Open findings for this host appear in{" "}
          <Link href="/findings" className="text-sky-400 hover:underline">
            Findings
          </Link>{" "}
          (filter by asset in a later iteration).
        </p>
      </Card>
    </div>
  );
}
