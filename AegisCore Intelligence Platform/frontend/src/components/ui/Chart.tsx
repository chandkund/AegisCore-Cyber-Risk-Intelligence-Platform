"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ChartContainerProps {
  children: ReactNode;
  title?: string;
  description?: string;
  className?: string;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  height?: number;
}

export function ChartContainer({
  children,
  title,
  description,
  className,
  loading = false,
  error,
  onRetry,
  height = 300,
}: ChartContainerProps) {
  if (loading) {
    return (
      <div
        className={cn(
          "rounded-xl border border-slate-700/50 bg-slate-800/50 p-6",
          className
        )}
      >
        {title && (
          <div className="mb-4">
            <div className="h-5 w-32 rounded bg-slate-700/50" />
            {description && (
              <div className="mt-2 h-3 w-48 rounded bg-slate-700/30" />
            )}
          </div>
        )}
        <div
          className="animate-pulse rounded bg-slate-700/30"
          style={{ height }}
        />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={cn(
          "rounded-xl border border-red-500/20 bg-red-500/5 p-6",
          className
        )}
      >
        {title && <h3 className="mb-2 text-lg font-semibold text-red-400">{title}</h3>}
        <p className="text-sm text-red-300/80">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-4 text-sm text-red-400 hover:text-red-300"
          >
            Try Again
          </button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "rounded-xl border border-slate-700/50 bg-slate-800/50 p-6",
        className
      )}
    >
      {(title || description) && (
        <div className="mb-4">
          {title && <h3 className="text-lg font-semibold text-slate-100">{title}</h3>}
          {description && (
            <p className="mt-1 text-sm text-slate-400">{description}</p>
          )}
        </div>
      )}
      <div style={{ height }}>{children}</div>
    </div>
  );
}

// Recharts theme configuration for dark mode
export const chartTheme = {
  colors: {
    critical: "#ef4444",
    high: "#f97316",
    medium: "#eab308",
    low: "#22c55e",
    info: "#3b82f6",
    slate: ["#94a3b8", "#64748b", "#475569", "#334155", "#1e293b"],
  },
  grid: {
    stroke: "#334155",
    strokeDasharray: "3 3",
  },
  text: {
    fill: "#94a3b8",
    fontSize: 12,
  },
  tooltip: {
    backgroundColor: "#1e293b",
    borderColor: "#334155",
    textColor: "#f8fafc",
  },
};
