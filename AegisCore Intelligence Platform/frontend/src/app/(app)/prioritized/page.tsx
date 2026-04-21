"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useVulnerabilities, type PrioritizedVulnerability, type Filters } from "@/hooks/useVulnerabilities";
import { PageHeader } from "@/components/ui/PageHeader";
import { FilterBar, FilterSelect } from "@/components/ui/FilterBar";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { DetailDrawer, DetailSection, DetailField } from "@/components/ui/DetailDrawer";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const statusColors: Record<string, string> = {
  OPEN: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  IN_PROGRESS: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  RESOLVED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  CLOSED: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

const LIMIT = 25;

export default function PrioritizedPage() {
  const { data, total, loading, error, fetchVulnerabilities } = useVulnerabilities();
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<Filters>({});
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null);
  const [selectedVulnerability, setSelectedVulnerability] = useState<PrioritizedVulnerability | null>(null);

  const loadData = useCallback(async () => {
    await fetchVulnerabilities(LIMIT, offset, filters);
  }, [fetchVulnerabilities, offset, filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleClearFilters = () => {
    setFilters({});
    setOffset(0);
  };

  const hasFilters = Object.values(filters).some((v) => v !== undefined && v !== "");

  const handleSort = (key: string) => {
    setSortConfig((current) => {
      if (current?.key === key) {
        return { key, direction: current.direction === "asc" ? "desc" : "asc" };
      }
      return { key, direction: "desc" };
    });
  };

  const sortedData = [...data].sort((a, b) => {
    if (!sortConfig) return 0;
    const aValue = a[sortConfig.key as keyof PrioritizedVulnerability];
    const bValue = b[sortConfig.key as keyof PrioritizedVulnerability];
    if (aValue === undefined || bValue === undefined) return 0;
    if (aValue < bValue) return sortConfig.direction === "asc" ? -1 : 1;
    if (aValue > bValue) return sortConfig.direction === "asc" ? 1 : -1;
    return 0;
  });

  const columns = [
    {
      key: "risk_score",
      header: "Risk Score",
      width: "120px",
      sortable: true,
      cell: (item: PrioritizedVulnerability) => (
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "h-2 w-2 rounded-full",
              item.risk_score >= 80 ? "bg-red-500" :
              item.risk_score >= 60 ? "bg-orange-500" :
              item.risk_score >= 40 ? "bg-amber-500" :
              "bg-emerald-500"
            )}
          />
          <span className="font-mono text-sm font-medium text-slate-200">
            {item.risk_score.toFixed(1)}
          </span>
        </div>
      ),
    },
    {
      key: "cve_id",
      header: "CVE ID",
      sortable: true,
      cell: (item: PrioritizedVulnerability) => (
        <Link
          href={`https://nvd.nist.gov/vuln/detail/${item.cve_id}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-sky-400 hover:text-sky-300 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {item.cve_id}
        </Link>
      ),
    },
    {
      key: "asset_name",
      header: "Asset",
      sortable: true,
      cell: (item: PrioritizedVulnerability) => (
        <div className="text-sm text-slate-200">{item.asset_name}</div>
      ),
    },
    {
      key: "cvss_score",
      header: "CVSS",
      width: "80px",
      sortable: true,
      cell: (item: PrioritizedVulnerability) => (
        <span className="font-mono text-sm text-slate-400">
          {item.cvss_score?.toFixed(1) || "N/A"}
        </span>
      ),
    },
    {
      key: "severity",
      header: "Severity",
      width: "100px",
      cell: (item: PrioritizedVulnerability) => {
        const severity = item.cvss_score >= 9 ? "CRITICAL" :
                        item.cvss_score >= 7 ? "HIGH" :
                        item.cvss_score >= 4 ? "MEDIUM" : "LOW";
        return (
          <Badge className={cn("text-xs", 
            severity === "CRITICAL" ? "bg-red-500/10 text-red-400" :
            severity === "HIGH" ? "bg-orange-500/10 text-orange-400" :
            severity === "MEDIUM" ? "bg-amber-500/10 text-amber-400" :
            "bg-emerald-500/10 text-emerald-400"
          )}>
            {severity}
          </Badge>
        );
      },
    },
    {
      key: "status",
      header: "Status",
      width: "120px",
      sortable: true,
      cell: (item: PrioritizedVulnerability) => (
        <Badge className={cn("text-xs", statusColors[item.status] || "bg-slate-500/10 text-slate-400")}>
          {item.status}
        </Badge>
      ),
    },
    {
      key: "discovered_at",
      header: "Discovered",
      width: "140px",
      sortable: true,
      cell: (item: PrioritizedVulnerability) => (
        <span className="text-sm text-slate-500">
          {new Date(item.discovered_at).toLocaleDateString()}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      width: "60px",
      cell: () => (
        <ChevronRight className="h-4 w-4 text-slate-600" />
      ),
    },
  ];

  if (error && !loading && data.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Prioritized Vulnerabilities"
          description="Risk-ranked vulnerabilities requiring attention"
        />
        <ErrorState title="Failed to load vulnerabilities" message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prioritized Vulnerabilities"
        description="Risk-ranked vulnerabilities requiring attention"
      />

      {/* Filters */}
      <FilterBar onClear={handleClearFilters} hasFilters={hasFilters}>
        <FilterSelect
          label="Status"
          value={filters.status || ""}
          options={[
            { value: "", label: "All Statuses" },
            { value: "OPEN", label: "Open" },
            { value: "IN_PROGRESS", label: "In Progress" },
            { value: "RESOLVED", label: "Resolved" },
            { value: "CLOSED", label: "Closed" },
          ]}
          onChange={(value) => setFilters((f) => ({ ...f, status: value || undefined }))}
        />
        <FilterSelect
          label="Min Risk Score"
          value={filters.minRiskScore?.toString() || ""}
          options={[
            { value: "", label: "Any Risk" },
            { value: "80", label: "Critical (80+)" },
            { value: "60", label: "High (60+)" },
            { value: "40", label: "Medium (40+)" },
          ]}
          onChange={(value) =>
            setFilters((f) => ({ ...f, minRiskScore: value ? parseInt(value) : undefined }))
          }
        />
      </FilterBar>

      {/* Table */}
      <DataTable
        data={sortedData}
        columns={columns}
        keyExtractor={(item) => item.id}
        loading={loading}
        error={error ?? undefined}
        onRetry={loadData}
        emptyState={
          <EmptyState
            type={hasFilters ? "search" : "default"}
            title={hasFilters ? "No matching vulnerabilities" : "No vulnerabilities found"}
            description={
              hasFilters
                ? "Try adjusting your filters to see more results"
                : "Upload vulnerability scan data to see prioritized findings"
            }
            action={
              hasFilters
                ? { label: "Clear Filters", onClick: handleClearFilters, variant: "outline" }
                : { label: "Upload Data", onClick: () => (window.location.href = "/uploads"), variant: "primary" }
            }
          />
        }
        onRowClick={(item: PrioritizedVulnerability) => setSelectedVulnerability(item)}
        pagination={{
          page: Math.floor(offset / LIMIT) + 1,
          pageSize: LIMIT,
          total,
          onPageChange: (page) => setOffset((page - 1) * LIMIT),
        }}
      />

      {/* Detail Drawer */}
      <DetailDrawer
        isOpen={!!selectedVulnerability}
        onClose={() => setSelectedVulnerability(null)}
        title={selectedVulnerability?.cve_id || "Vulnerability Details"}
        subtitle={selectedVulnerability?.asset_name}
        footer={
          <div className="flex gap-3">
            <Link href={`/findings/${selectedVulnerability?.id}`} className="flex-1">
              <Button variant="primary" className="w-full">
                View Full Details
              </Button>
            </Link>
          </div>
        }
      >
        {selectedVulnerability && (
          <>
            <DetailSection title="Risk Assessment">
              <div className="grid grid-cols-2 gap-4">
                <DetailField
                  label="Risk Score"
                  value={
                    <span className={cn(
                      "text-lg font-semibold",
                      selectedVulnerability.risk_score >= 80 ? "text-red-400" :
                      selectedVulnerability.risk_score >= 60 ? "text-orange-400" :
                      selectedVulnerability.risk_score >= 40 ? "text-amber-400" :
                      "text-emerald-400"
                    )}>
                      {selectedVulnerability.risk_score.toFixed(1)}
                    </span>
                  }
                />
                <DetailField
                  label="CVSS Score"
                  value={
                    <span className="font-mono text-slate-200">
                      {selectedVulnerability.cvss_score?.toFixed(1) || "N/A"}
                    </span>
                  }
                />
              </div>
            </DetailSection>

            <DetailSection title="Details">
              <DetailField label="Asset" value={selectedVulnerability.asset_name} />
              <DetailField label="Asset Criticality" value={selectedVulnerability.asset_criticality} />
              <DetailField
                label="Discovered"
                value={new Date(selectedVulnerability.discovered_at).toLocaleString()}
              />
              {selectedVulnerability.due_at && (
                <DetailField
                  label="Due Date"
                  value={new Date(selectedVulnerability.due_at).toLocaleString()}
                />
              )}
            </DetailSection>

            <DetailSection title="Status">
              <div className="flex items-center gap-2">
                <Badge className={statusColors[selectedVulnerability.status] || "bg-slate-500/10 text-slate-400"}>
                  {selectedVulnerability.status}
                </Badge>
              </div>
            </DetailSection>

            {selectedVulnerability.risk_factors && (
              <DetailSection title="Risk Factors">
                <div className="space-y-2">
                  {Object.entries(selectedVulnerability.risk_factors).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm text-slate-400 capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="font-mono text-sm text-slate-200">
                        {typeof value === "number" ? value.toFixed(2) : value}
                      </span>
                    </div>
                  ))}
                </div>
              </DetailSection>
            )}
          </>
        )}
      </DetailDrawer>
    </div>
  );
}
