"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  Info,
} from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    label: string;
    direction: "up" | "down" | "neutral";
  };
  icon?: ReactNode;
  status?: "success" | "warning" | "error" | "info" | "neutral";
  className?: string;
  loading?: boolean;
}

const statusColors = {
  success: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    icon: "text-emerald-400",
    glow: "shadow-emerald-500/10",
  },
  warning: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    icon: "text-amber-400",
    glow: "shadow-amber-500/10",
  },
  error: {
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    icon: "text-red-400",
    glow: "shadow-red-500/10",
  },
  info: {
    bg: "bg-sky-500/10",
    border: "border-sky-500/20",
    icon: "text-sky-400",
    glow: "shadow-sky-500/10",
  },
  neutral: {
    bg: "bg-slate-500/10",
    border: "border-slate-500/20",
    icon: "text-slate-400",
    glow: "shadow-slate-500/10",
  },
};

const statusIcons = {
  success: <CheckCircle className="h-5 w-5" />,
  warning: <AlertCircle className="h-5 w-5" />,
  error: <AlertCircle className="h-5 w-5" />,
  info: <Info className="h-5 w-5" />,
  neutral: <Info className="h-5 w-5" />,
};

export function KpiCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  status = "neutral",
  className,
  loading = false,
}: KpiCardProps) {
  const colors = statusColors[status];
  const statusIcon = statusIcons[status];

  if (loading) {
    return (
      <div
        className={cn(
          "rounded-xl border border-slate-700/50 bg-slate-800/50 p-6",
          "animate-pulse",
          className
        )}
      >
        <div className="flex items-start justify-between">
          <div className="space-y-3">
            <div className="h-4 w-24 rounded bg-slate-700/50" />
            <div className="h-8 w-16 rounded bg-slate-700/50" />
            <div className="h-3 w-32 rounded bg-slate-700/50" />
          </div>
          <div className="h-10 w-10 rounded-lg bg-slate-700/50" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border p-6 transition-all duration-300",
        "hover:scale-[1.02] hover:shadow-lg",
        colors.bg,
        colors.border,
        colors.glow,
        className
      )}
    >
      {/* Subtle gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />

      <div className="relative flex items-start justify-between">
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <p className="text-3xl font-bold tracking-tight text-slate-100">
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-slate-500">{subtitle}</p>
          )}
          {trend && (
            <div className="flex items-center gap-1.5 pt-1">
              {trend.direction === "up" && (
                <TrendingUp
                  className={cn(
                    "h-3.5 w-3.5",
                    trend.value >= 0 ? "text-emerald-400" : "text-red-400"
                  )}
                />
              )}
              {trend.direction === "down" && (
                <TrendingDown
                  className={cn(
                    "h-3.5 w-3.5",
                    trend.value <= 0 ? "text-emerald-400" : "text-red-400"
                  )}
                />
              )}
              {trend.direction === "neutral" && (
                <Minus className="h-3.5 w-3.5 text-slate-400" />
              )}
              <span
                className={cn(
                  "text-xs font-medium",
                  trend.value > 0
                    ? "text-emerald-400"
                    : trend.value < 0
                      ? "text-red-400"
                      : "text-slate-400"
                )}
              >
                {trend.value > 0 ? "+" : ""}
                {trend.value}% {trend.label}
              </span>
            </div>
          )}
        </div>
        <div
          className={cn(
            "flex h-12 w-12 items-center justify-center rounded-xl border bg-slate-900/50 backdrop-blur-sm",
            colors.border,
            colors.icon
          )}
        >
          {icon || statusIcon}
        </div>
      </div>
    </div>
  );
}
