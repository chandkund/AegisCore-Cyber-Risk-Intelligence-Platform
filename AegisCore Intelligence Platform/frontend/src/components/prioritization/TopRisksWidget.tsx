"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getTopRisks } from "@/lib/api";
import type { PrioritizedFindingOut } from "@/types/api";
import { Card } from "@/components/ui/Card";
import { RiskScoreBadge } from "./RiskScoreBadge";

export function TopRisksWidget() {
  const [risks, setRisks] = useState<PrioritizedFindingOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTopRisks() {
      try {
        setLoading(true);
        const data = await getTopRisks(5, 60); // Top 5 with risk >= 60
        if (data) {
          setRisks(data);
        } else {
          setError("Failed to load top risks");
        }
      } catch (err) {
        setError("Error loading risks");
      } finally {
        setLoading(false);
      }
    }

    loadTopRisks();
  }, []);

  if (loading) {
    return (
      <Card title="Top Risks">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded bg-surface-muted" />
          ))}
        </div>
      </Card>
    );
  }

  if (error || risks.length === 0) {
    return (
      <Card title="Top Risks">
        <div className="py-8 text-center text-sm text-slate-400">
          {error || "No high-risk vulnerabilities found"}
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg text-rose-300">⚠️</span>
          <h3 className="text-lg font-semibold text-app-fg">Top Risks</h3>
        </div>
        <Link
          href="/prioritized"
          className="text-sm text-accent hover:text-accent-hover"
        >
          View all →
        </Link>
      </div>

      <div className="space-y-3">
        {risks.map((risk) => (
          <div
            key={risk.id}
            className="flex items-center gap-4 rounded-lg border border-app-border bg-surface p-3 transition-colors hover:bg-surface-muted"
          >
            <RiskScoreBadge score={risk.risk_score} size="sm" />

            <div className="flex-1 min-w-0">
              <Link
                href={`/findings/${risk.id}`}
                className="block truncate font-medium text-app-fg hover:text-accent"
              >
                {risk.cve_id || "Unknown CVE"}
              </Link>
              <div className="truncate text-sm text-slate-400">
                {risk.asset_name || "Unknown asset"}
                {risk.asset_criticality && (
                  <span className="ml-2 rounded bg-surface-muted px-2 py-0.5 text-xs text-slate-300">
                    Criticality {risk.asset_criticality}
                  </span>
                )}
              </div>
            </div>

            <Link
              href={`/findings/${risk.id}`}
              className="text-sm text-accent hover:text-accent-hover"
            >
              View →
            </Link>
          </div>
        ))}
      </div>
    </Card>
  );
}
