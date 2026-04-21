"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { FileX, Upload, Plus } from "lucide-react";
import { Button } from "./Button";

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  action?: {
    label: string;
    onClick: () => void;
    variant?: "primary" | "outline" | "ghost";
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  type?: "default" | "upload" | "search" | "custom";
}

const defaultIcons = {
  default: <FileX className="h-12 w-12" />,
  upload: <Upload className="h-12 w-12" />,
  search: <FileX className="h-12 w-12" />,
  custom: null,
};

export function EmptyState({
  title = "No data available",
  description = "Get started by uploading data or creating your first item.",
  icon,
  action,
  secondaryAction,
  className,
  type = "default",
}: EmptyStateProps) {
  const defaultIcon = defaultIcons[type];

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-slate-700/50 bg-slate-800/30 px-6 py-12 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-slate-800/80 text-slate-500">
        {icon || defaultIcon}
      </div>
      
      <h3 className="mb-2 text-lg font-semibold text-slate-200">
        {title}
      </h3>
      
      <p className="mb-6 max-w-sm text-sm text-slate-400">
        {description}
      </p>
      
      <div className="flex flex-col gap-2 sm:flex-row">
        {action && (
          <Button
            onClick={action.onClick}
            variant={action.variant || "primary"}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            {action.label}
          </Button>
        )}
        
        {secondaryAction && (
          <Button
            onClick={secondaryAction.onClick}
            variant="outline"
            className="border-slate-600 text-slate-300 hover:bg-slate-800"
          >
            {secondaryAction.label}
          </Button>
        )}
      </div>
    </div>
  );
}

// Specialized empty states for common use cases
export function EmptyStateUpload({
  onUpload,
  className,
}: {
  onUpload: () => void;
  className?: string;
}) {
  return (
    <EmptyState
      type="upload"
      title="No data uploaded yet"
      description="Upload your vulnerability scan results or asset inventory to start analyzing your security posture."
      action={{
        label: "Upload Data",
        onClick: onUpload,
      }}
      className={className}
    />
  );
}

export function EmptyStateSearch({
  searchTerm,
  onClear,
  className,
}: {
  searchTerm: string;
  onClear: () => void;
  className?: string;
}) {
  return (
    <EmptyState
      type="search"
      title="No results found"
      description={`We couldn't find any results for "${searchTerm}". Try adjusting your search terms.`}
      action={{
        label: "Clear Search",
        onClick: onClear,
        variant: "outline",
      }}
      className={className}
    />
  );
}
