"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAssets, type Asset, type AssetsFilters } from "@/hooks/useAssets";
import { PageHeader } from "@/components/ui/PageHeader";
import { FilterBar, FilterSelect, FilterSearch } from "@/components/ui/FilterBar";
import { DataTable } from "@/components/ui/DataTable";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { DetailDrawer, DetailSection, DetailField } from "@/components/ui/DetailDrawer";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ChevronRight, Server, Shield, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

const criticalityColors: Record<number, string> = {
  1: "bg-red-500/10 text-red-400 border-red-500/20",
  2: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  3: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  4: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

const LIMIT = 25;

export default function AssetsPage() {
  const { data, total, loading, error, selectedAsset, fetchAssets, fetchAssetDetail, setSelectedAsset } = useAssets();
  const [offset, setOffset] = useState(0);
  const [filters, setFilters] = useState<AssetsFilters>({});
  const [detailOpen, setDetailOpen] = useState(false);

  const loadData = useCallback(async () => {
    await fetchAssets(LIMIT, offset, filters);
  }, [fetchAssets, offset, filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleClearFilters = () => {
    setFilters({});
    setOffset(0);
  };

  const hasFilters = Object.values(filters).some((v) => v !== undefined && v !== "");

  const handleRowClick = async (asset: Asset) => {
    await fetchAssetDetail(asset.id);
    setDetailOpen(true);
  };

  const columns = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      cell: (item: Asset) => (
        <div className="flex items-center gap-2">
          <Server className="h-4 w-4 text-slate-500" />
          <span className="font-medium text-sm text-slate-200">{item.name}</span>
        </div>
      ),
    },
    {
      key: "type",
      header: "Type",
      width: "120px",
      sortable: true,
      cell: (item: Asset) => (
        <Badge variant="outline" className="text-xs">
          {item.type}
        </Badge>
      ),
    },
    {
      key: "criticality",
      header: "Criticality",
      width: "100px",
      sortable: true,
      cell: (item: Asset) => {
        const labels: Record<number, string> = { 1: "Critical", 2: "High", 3: "Medium", 4: "Low" };
        return (
          <Badge className={cn("text-xs", criticalityColors[item.criticality] || "bg-slate-500/10 text-slate-400")}>
            {labels[item.criticality] || item.criticality}
          </Badge>
        );
      },
    },
    {
      key: "ip_address",
      header: "IP Address",
      width: "140px",
      cell: (item: Asset) => (
        <span className="font-mono text-sm text-slate-400">
          {item.ip_address || "—"}
        </span>
      ),
    },
    {
      key: "open_findings_count",
      header: "Open Findings",
      width: "120px",
      sortable: true,
      cell: (item: Asset) => (
        <div className="flex items-center gap-1">
          {(item.open_findings_count || 0) > 0 ? (
            <>
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-sm font-medium text-amber-400">
                {item.open_findings_count}
              </span>
            </>
          ) : (
            <>
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-sm text-emerald-400">0</span>
            </>
          )}
        </div>
      ),
    },
    {
      key: "max_risk_score",
      header: "Risk Score",
      width: "100px",
      sortable: true,
      cell: (item: Asset) => {
        const score = item.max_risk_score || 0;
        return (
          <span className={cn(
            "font-mono text-sm",
            score >= 80 ? "text-red-400" :
            score >= 60 ? "text-orange-400" :
            score >= 40 ? "text-amber-400" :
            "text-emerald-400"
          )}>
            {score > 0 ? score.toFixed(1) : "—"}
          </span>
        );
      },
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
          title="Asset Inventory"
          description="View and manage your IT assets"
        />
        <ErrorState title="Failed to load assets" message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Asset Inventory"
        description="View and manage your IT assets"
      />

      {/* Filters */}
      <FilterBar onClear={handleClearFilters} hasFilters={hasFilters}>
        <FilterSearch
          placeholder="Search assets..."
          value={filters.search || ""}
          onChange={(value) => setFilters((f) => ({ ...f, search: value || undefined }))}
          className="min-w-[240px]"
        />
        <FilterSelect
          label="Criticality"
          value={filters.criticality?.toString() || ""}
          options={[
            { value: "", label: "All Criticalities" },
            { value: "1", label: "Critical" },
            { value: "2", label: "High" },
            { value: "3", label: "Medium" },
            { value: "4", label: "Low" },
          ]}
          onChange={(value) =>
            setFilters((f) => ({ ...f, criticality: value ? parseInt(value) : undefined }))
          }
        />
        <FilterSelect
          label="Type"
          value={filters.type || ""}
          options={[
            { value: "", label: "All Types" },
            { value: "SERVER", label: "Server" },
            { value: "WORKSTATION", label: "Workstation" },
            { value: "NETWORK", label: "Network" },
            { value: "CLOUD", label: "Cloud" },
            { value: "CONTAINER", label: "Container" },
          ]}
          onChange={(value) => setFilters((f) => ({ ...f, type: value || undefined }))}
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
            title={hasFilters ? "No matching assets" : "No assets found"}
            description={
              hasFilters
                ? "Try adjusting your filters to see more results"
                : "Import your IT assets to begin tracking vulnerabilities"
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
          setSelectedAsset(null);
        }}
        title={selectedAsset?.name || "Asset Details"}
        subtitle={selectedAsset?.type}
        footer={
          <div className="flex gap-3">
            <Link href={`/assets/${selectedAsset?.id}`} className="flex-1">
              <Button variant="primary" className="w-full">
                View Full Details
              </Button>
            </Link>
          </div>
        }
      >
        {selectedAsset && (
          <>
            <DetailSection title="Asset Information">
              <DetailField label="Name" value={selectedAsset.name} />
              <DetailField label="Type" value={selectedAsset.type} />
              <DetailField
                label="Criticality"
                value={
                  <Badge className={criticalityColors[selectedAsset.criticality] || "bg-slate-500/10 text-slate-400"}>
                    {selectedAsset.criticality === 1 ? "Critical" :
                     selectedAsset.criticality === 2 ? "High" :
                     selectedAsset.criticality === 3 ? "Medium" : "Low"}
                  </Badge>
                }
              />
              {selectedAsset.description && (
                <DetailField label="Description" value={selectedAsset.description} />
              )}
            </DetailSection>

            <DetailSection title="Network">
              <DetailField label="IP Address" value={selectedAsset.ip_address || "N/A"} />
              {selectedAsset.hostname && (
                <DetailField label="Hostname" value={selectedAsset.hostname} />
              )}
              {selectedAsset.os_family && (
                <DetailField label="OS Family" value={selectedAsset.os_family} />
              )}
            </DetailSection>

            {(selectedAsset.cloud_provider || selectedAsset.region) && (
              <DetailSection title="Cloud">
                {selectedAsset.cloud_provider && (
                  <DetailField label="Provider" value={selectedAsset.cloud_provider} />
                )}
                {selectedAsset.region && (
                  <DetailField label="Region" value={selectedAsset.region} />
                )}
              </DetailSection>
            )}

            <DetailSection title="Risk Summary">
              <DetailField
                label="Open Findings"
                value={
                  <span className={cn(
                    "font-mono",
                    (selectedAsset.open_findings_count || 0) > 0 ? "text-amber-400" : "text-emerald-400"
                  )}>
                    {selectedAsset.open_findings_count || 0}
                  </span>
                }
              />
              <DetailField
                label="Max Risk Score"
                value={
                  <span className={cn(
                    "font-mono",
                    (selectedAsset.max_risk_score || 0) >= 80 ? "text-red-400" :
                    (selectedAsset.max_risk_score || 0) >= 60 ? "text-orange-400" :
                    (selectedAsset.max_risk_score || 0) >= 40 ? "text-amber-400" :
                    "text-emerald-400"
                  )}>
                    {selectedAsset.max_risk_score?.toFixed(1) || "N/A"}
                  </span>
                }
              />
            </DetailSection>

            {selectedAsset.tags && Object.keys(selectedAsset.tags).length > 0 && (
              <DetailSection title="Tags">
                <div className="flex flex-wrap gap-2">
                  {Object.entries(selectedAsset.tags).map(([key, value]) => (
                    <Badge key={key} variant="outline" className="text-xs">
                      {key}: {value}
                    </Badge>
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
