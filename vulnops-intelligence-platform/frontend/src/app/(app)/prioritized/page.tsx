"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { getPrioritizedVulnerabilities } from "@/lib/api";
import type { PrioritizedFindingOut } from "@/types/api";
import { RiskScoreBadge, RiskScoreBar } from "@/components/prioritization/RiskScoreBadge";
import { RequireAuth } from "@/components/auth/RequireAuth";

export default function PrioritizedFindingsPage() {
  return (
    <RequireAuth>
      <PrioritizedContent />
    </RequireAuth>
  );
}

function PrioritizedContent() {
  const [findings, setFindings] = useState<PrioritizedFindingOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  const [minRiskScore, setMinRiskScore] = useState<number | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string>("OPEN");

  useEffect(() => {
    async function loadFindings() {
      try {
        setLoading(true);
        const data = await getPrioritizedVulnerabilities({
          limit,
          offset,
          min_risk_score: minRiskScore,
          status: statusFilter,
        });
        if (data) {
          setFindings(data.items);
          setTotal(data.total);
        } else {
          setError("Failed to load prioritized vulnerabilities");
        }
      } catch (err) {
        setError("Error loading data");
      } finally {
        setLoading(false);
      }
    }

    loadFindings();
  }, [offset, minRiskScore, statusFilter]);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Prioritized Vulnerabilities</h1>
        <p className="text-gray-600 mt-1">
          Ranked by risk score — highest risk vulnerabilities that need immediate attention
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Minimum Risk Score
            </label>
            <select
              value={minRiskScore || ""}
              onChange={(e) => {
                const val = e.target.value;
                setMinRiskScore(val ? parseInt(val) : undefined);
                setOffset(0);
              }}
              className="border border-gray-300 rounded-md bg-white px-3 py-2 text-sm text-gray-900 [color-scheme:light]"
            >
              <option value="" className="text-gray-900 bg-white">All scores</option>
              <option value="80" className="text-gray-900 bg-white">Critical (80+)</option>
              <option value="60" className="text-gray-900 bg-white">High (60+)</option>
              <option value="40" className="text-gray-900 bg-white">Medium (40+)</option>
              <option value="20" className="text-gray-900 bg-white">Low (20+)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setOffset(0);
              }}
              className="border border-gray-300 rounded-md bg-white px-3 py-2 text-sm text-gray-900 [color-scheme:light]"
            >
              <option value="OPEN" className="text-gray-900 bg-white">Open</option>
              <option value="IN_PROGRESS" className="text-gray-900 bg-white">In Progress</option>
              <option value="" className="text-gray-900 bg-white">All statuses</option>
            </select>
          </div>

          <div className="ml-auto text-sm text-gray-500">
            Showing {findings.length} of {total} vulnerabilities
          </div>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-red-700">
          {error}
        </div>
      ) : findings.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-12 text-center">
          <p className="text-gray-500 text-lg">No vulnerabilities match the current filters</p>
          <button
            onClick={() => {
              setMinRiskScore(undefined);
              setStatusFilter("OPEN");
              setOffset(0);
            }}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            Clear filters
          </button>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {findings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={currentPage >= totalPages}
                className="px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: PrioritizedFindingOut }) {
  const factors = finding.risk_factors || {};
  const contributing = (factors.contributing_factors || []) as Array<{
    factor: string;
    description: string;
    impact: string;
  }>;

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-5">
      <div className="flex items-start gap-4">
        <RiskScoreBadge score={finding.risk_score} size="md" showLabel />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link
              href={`/findings/${finding.id}`}
              className="text-lg font-semibold text-blue-600 hover:text-blue-800"
            >
              {finding.cve_id || "Unknown CVE"}
            </Link>
            <span
              className={`px-2 py-0.5 text-xs rounded-full ${
                finding.status === "OPEN"
                  ? "bg-yellow-100 text-yellow-800"
                  : finding.status === "IN_PROGRESS"
                  ? "bg-blue-100 text-blue-800"
                  : "bg-green-100 text-green-800"
              }`}
            >
              {finding.status}
            </span>
            {finding.asset_criticality && finding.asset_criticality <= 2 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800">
                Critical Asset
              </span>
            )}
          </div>

          <div className="mt-2 text-sm text-gray-600">
            <span className="font-medium">Asset:</span> {finding.asset_name || "Unknown"}
            {finding.cvss_score && (
              <span className="ml-4">
                <span className="font-medium">CVSS:</span> {finding.cvss_score.toFixed(1)}
              </span>
            )}
            <span className="ml-4">
              <span className="font-medium">Discovered:</span>{" "}
              {new Date(finding.discovered_at).toLocaleDateString()}
            </span>
          </div>

          {/* Contributing Factors */}
          {contributing.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {contributing.slice(0, 3).map((factor, idx) => (
                <span
                  key={idx}
                  className={`text-xs px-2 py-1 rounded ${
                    factor.impact === "high"
                      ? "bg-red-100 text-red-700"
                      : factor.impact === "medium"
                      ? "bg-orange-100 text-orange-700"
                      : "bg-gray-100 text-gray-700"
                  }`}
                  title={factor.description}
                >
                  {factor.description}
                </span>
              ))}
            </div>
          )}

          {/* Risk Score Bar */}
          <div className="mt-3">
            <RiskScoreBar score={finding.risk_score} height="h-1.5" showValue={false} />
          </div>
        </div>

        <Link
          href={`/findings/${finding.id}`}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
        >
          View Details
        </Link>
      </div>
    </div>
  );
}
