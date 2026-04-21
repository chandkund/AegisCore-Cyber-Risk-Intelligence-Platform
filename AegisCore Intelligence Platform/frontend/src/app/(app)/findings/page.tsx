"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useFindings, type Finding, type FindingsFilters } from "@/hooks/useFindings";
import { PageHeader } from "@/components/ui/PageHeader";
import { FilterBar, FilterSelect, FilterSearch } from "@/components/ui/FilterBar";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { DetailDrawer, DetailSection, DetailField } from "@/components/ui/DetailDrawer";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

const severityColors: Record<string, string> = {
  CRITICAL: "bg-red-500/10 text-red-400 border-red-500/20",
  HIGH: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  MEDIUM: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  LOW: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

const statusColors: Record<string, string> = {
  OPEN: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  IN_PROGRESS: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  RESOLVED: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  CLOSED: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

const LIMIT = 25;

export default function FindingsPage() {
  const { data, total, loading, error, selectedFinding, fetchFindings, fetchFindingDetail, setSelectedFinding } = useFindings();
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<FindingsFilters>({});
  const [detailOpen, setDetailOpen] = useState(false);

  const loadData = useCallback(async () => {
    await fetchFindings(LIMIT, offset, filters);
  }, [fetchFindings, offset, filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleClearFilters = () => {
    setFilters({});
    setOffset(0);
  };

  const hasFilters = Object.values(filters).some((v) => v !== undefined && v !== "");

  const handleRowClick = async (finding: Finding) => {
    await fetchFindingDetail(finding.id);
    setDetailOpen(true);
  };

  const columns = [
    {
      key: "cve_id",
      header: "CVE ID",
      sortable: true,
      cell: (item: Finding) => (
        item.cve_id ? (
          <Link
            href={`https://nvd.nist.gov/vuln/detail/${item.cve_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-sky-400 hover:text-sky-300 hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {item.cve_id}
          </Link>
        ) : (
          <span className="text-sm text-slate-500">—</span>
        )
      ),
    },
    {
      key: "asset_name",
      header: "Asset",
      sortable: true,
      cell: (item: Finding) => (
        <div className="text-sm text-slate-200">{item.asset_name}</div>
      ),
    },
    {
      key: "severity",
      header: "Severity",
      width: "100px",
      sortable: true,
      cell: (item: Finding) => (
        <Badge className={cn("text-xs", severityColors[item.severity] || "bg-slate-500/10 text-slate-400")}>
          {item.severity}
        </Badge>
      ),
    },
    {
      key: "cvss_score",
      header: "CVSS",
      width: "80px",
      sortable: true,
      cell: (item: Finding) => (
        <span className="font-mono text-sm text-slate-400">
          {item.cvss_score?.toFixed(1) || "N/A"}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      width: "120px",
      sortable: true,
      cell: (item: Finding) => (
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
      cell: (item: Finding) => (
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
          title="Findings"
          description="Complete vulnerability findings inventory"
        />
        <ErrorState title="Failed to load findings" message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Findings"
        description="Complete vulnerability findings inventory"
      />

      {/* Filters */}
      <FilterBar onClear={handleClearFilters} hasFilters={hasFilters}>
        <FilterSearch
          placeholder="Search CVE, asset..."
          value={filters.search || ""}
          onChange={(value) => setFilters((f) => ({ ...f, search: value || undefined }))}
          className="min-w-[240px]"
        />
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
          label="Severity"
          value={filters.severity || ""}
          options={[
            { value: "", label: "All Severities" },
            { value: "CRITICAL", label: "Critical" },
            { value: "HIGH", label: "High" },
            { value: "MEDIUM", label: "Medium" },
            { value: "LOW", label: "Low" },
          ]}
          onChange={(value) => setFilters((f) => ({ ...f, severity: value || undefined }))}
        />
      </FilterBar>

      {/* Table */}
      <DataTable
        data={data}
        columns={columns}
        keyExtractor={(item) => item.id}
        loading={loading}
        error={error ?? undefined}
        onRetry={loadData}
        emptyState={
          <EmptyState
            type={hasFilters ? "search" : "default"}
            title={hasFilters ? "No matching findings" : "No findings found"}
            description={
              hasFilters
                ? "Try adjusting your filters to see more results"
                : "Upload vulnerability scan data to see findings"
            }
            action={
              hasFilters
                ? { label: "Clear Filters", onClick: handleClearFilters, variant: "outline" }
                : { label: "Upload Data", onClick: () => (window.location.href = "/uploads"), variant: "primary" }
            }
          />
        }
        onRowClick={handleRowClick}
        pagination={{
          page: Math.floor(offset / LIMIT) + 1,
          pageSize: LIMIT,
          total,
          onPageChange: (page) => setOffset((page - 1) * LIMIT),
        }}
      />

      {/* Detail Drawer */}
      <DetailDrawer
        isOpen={detailOpen}
        onClose={() => {
          setDetailOpen(false);
          setSelectedFinding(null);
        }}
        title={selectedFinding?.cve_id || "Finding Details"}
        subtitle={selectedFinding?.asset_name}
        footer={
          <div className="flex gap-3">
            <Link href={`/findings/${selectedFinding?.id}`} className="flex-1">
              <Button variant="primary" className="w-full">
                View Full Details
              </Button>
            </Link>
          </div>
        }
      >
        {selectedFinding && (
          <>
            <DetailSection title="Vulnerability Information">
              <DetailField label="CVE ID" value={selectedFinding.cve_id || "N/A"} />
              <DetailField label="Asset" value={selectedFinding.asset_name} />
              <DetailField
                label="Severity"
                value={
                  <Badge className={severityColors[selectedFinding.severity] || "bg-slate-500/10 text-slate-400"}>
                    {selectedFinding.severity}
                  </Badge>
                }
              />
              <DetailField
                label="CVSS Score"
                value={
                  <span className="font-mono text-slate-200">
                    {selectedFinding.cvss_score?.toFixed(1) || "N/A"}
                  </span>
                }
              />
              <DetailField
                label="Risk Score"
                value={
                  <span className="font-mono text-slate-200">
                    {selectedFinding.risk_score?.toFixed(1) || "N/A"}
                  </span>
                }
              />
            </DetailSection>

            <DetailSection title="Details">
              <DetailField
                label="Status"
                value={
                  <Badge className={statusColors[selectedFinding.status] || "bg-slate-500/10 text-slate-400"}>
                    {selectedFinding.status}
                  </Badge>
                }
              />
              <DetailField
                label="Discovered"
                value={new Date(selectedFinding.discovered_at).toLocaleString()}
              />
              {selectedFinding.last_seen_at && (
                <DetailField
                  label="Last Seen"
                  value={new Date(selectedFinding.last_seen_at).toLocaleString()}
                />
              )}
              {selectedFinding.service_name && (
                <DetailField label="Service" value={selectedFinding.service_name} />
              )}
              {selectedFinding.port && (
                <DetailField label="Port" value={selectedFinding.port.toString()} />
              )}
            </DetailSection>

            {selectedFinding.description && (
              <DetailSection title="Description">
                <p className="text-sm text-slate-300 whitespace-pre-wrap">
                  {selectedFinding.description}
                </p>
              </DetailSection>
            )}

            {selectedFinding.remediation && (
              <DetailSection title="Remediation">
                <p className="text-sm text-slate-300 whitespace-pre-wrap">
                  {selectedFinding.remediation}
                </p>
              </DetailSection>
            )}
          </>
        )}
      </DetailDrawer>
    </div>
  );
}
