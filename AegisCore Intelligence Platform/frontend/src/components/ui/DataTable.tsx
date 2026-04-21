"use client";

import { ReactNode, useState } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronUp, ArrowUpDown } from "lucide-react";
import { Button } from "./Button";

interface Column<T> {
  key: string;
  header: string;
  width?: string;
  sortable?: boolean;
  cell: (item: T) => ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  keyExtractor: (item: T) => string;
  loading?: boolean;
  emptyState?: ReactNode;
  error?: string;
  onRetry?: () => void;
  className?: string;
  sortable?: boolean;
  onRowClick?: (item: T) => void;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}

export function DataTable<T>({
  data,
  columns,
  keyExtractor,
  loading = false,
  emptyState,
  error,
  onRetry,
  className,
  sortable = true,
  onRowClick,
  pagination,
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<{
    key: string;
    direction: "asc" | "desc";
  } | null>(null);

  const handleSort = (key: string) => {
    if (!sortable) return;
    setSortConfig((current) => {
      if (current?.key === key) {
        return {
          key,
          direction: current.direction === "asc" ? "desc" : "asc",
        };
      }
      return { key, direction: "asc" };
    });
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className={cn("rounded-xl border border-slate-700/50 bg-slate-800/50", className)}>
        <div className="p-4">
          {/* Header skeleton */}
          <div className="flex gap-4 border-b border-slate-700/50 pb-4">
            {columns.map((col, i) => (
              <div
                key={i}
                className="h-4 flex-1 rounded bg-slate-700/50"
                style={{ width: col.width }}
              />
            ))}
          </div>
          {/* Rows skeleton */}
          {[...Array(5)].map((_, rowIdx) => (
            <div
              key={rowIdx}
              className="flex gap-4 border-b border-slate-700/30 py-4 last:border-0"
            >
              {columns.map((_, colIdx) => (
                <div
                  key={colIdx}
                  className="h-4 flex-1 rounded bg-slate-700/30"
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn("rounded-xl border border-red-500/20 bg-red-500/5 p-8 text-center", className)}>
        <p className="text-red-400">{error}</p>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="mt-4 border-red-500/30 text-red-400 hover:bg-red-500/10"
          >
            Retry
          </Button>
        )}
      </div>
    );
  }

  // Empty state
  if (data.length === 0) {
    return (
      <div className={cn("rounded-xl border border-slate-700/50 bg-slate-800/50 p-8 text-center", className)}>
        {emptyState || (
          <>
            <p className="text-slate-400">No data available</p>
            <p className="mt-1 text-sm text-slate-500">
              Upload data to see results here
            </p>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={cn("overflow-hidden rounded-xl border border-slate-700/50 bg-slate-800/50", className)}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700/50 bg-slate-800/80">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400",
                    column.sortable && sortable && "cursor-pointer hover:text-slate-300"
                  )}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column.key)}
                >
                  <div className="flex items-center gap-1">
                    {column.header}
                    {column.sortable && sortable && (
                      <span className="ml-1">
                        {sortConfig?.key === column.key ? (
                          sortConfig.direction === "asc" ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )
                        ) : (
                          <ArrowUpDown className="h-3.5 w-3.5 opacity-30" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((item, index) => (
              <tr
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                className={cn(
                  "border-b border-slate-700/30 transition-colors hover:bg-slate-700/20",
                  index % 2 === 0 ? "bg-slate-800/30" : "bg-slate-800/10",
                  onRowClick && "cursor-pointer"
                )}
              >
                {columns.map((column) => (
                  <td key={column.key} className="px-4 py-3">
                    {column.cell(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && (
        <div className="flex items-center justify-between border-t border-slate-700/50 px-4 py-3">
          <p className="text-sm text-slate-500">
            Showing {(pagination.page - 1) * pagination.pageSize + 1} to{" "}
            {Math.min(pagination.page * pagination.pageSize, pagination.total)} of{" "}
            {pagination.total} results
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page * pagination.pageSize >= pagination.total}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
