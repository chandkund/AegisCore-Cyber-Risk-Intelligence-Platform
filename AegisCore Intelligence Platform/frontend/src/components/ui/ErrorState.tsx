"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message = "We encountered an error while loading this data. Please try again.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 px-6 py-12 text-center",
        className
      )}
    >
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10 text-red-400">
        <AlertTriangle className="h-8 w-8" />
      </div>
      
      <h3 className="mb-2 text-lg font-semibold text-red-400">
        {title}
      </h3>
      
      <p className="mb-6 max-w-sm text-sm text-red-300/80">
        {message}
      </p>
      
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="outline"
          className="gap-2 border-red-500/30 text-red-400 hover:bg-red-500/10"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </Button>
      )}
    </div>
  );
}
