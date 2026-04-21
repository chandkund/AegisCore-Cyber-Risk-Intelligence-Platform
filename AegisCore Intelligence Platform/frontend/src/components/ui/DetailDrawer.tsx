"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { X, ChevronRight } from "lucide-react";
import { Button } from "./Button";

interface DetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  footer?: ReactNode;
}

export function DetailDrawer({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  className,
  footer,
}: DetailDrawerProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div
        className={cn(
          "fixed inset-y-0 right-0 z-50 w-full max-w-lg",
          "transform transition-transform duration-300 ease-in-out",
          "bg-slate-900 border-l border-slate-700/50",
          "shadow-2xl shadow-black/50",
          "flex flex-col",
          isOpen ? "translate-x-0" : "translate-x-full",
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
            {subtitle && (
              <p className="text-sm text-slate-500">{subtitle}</p>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="border-t border-slate-800 px-6 py-4">{footer}</div>
        )}
      </div>
    </>
  );
}

interface DetailSectionProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export function DetailSection({ title, children, className }: DetailSectionProps) {
  return (
    <div className={cn("mb-6", className)}>
      <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500">
        {title}
      </h3>
      {children}
    </div>
  );
}

interface DetailFieldProps {
  label: string;
  value: ReactNode;
  className?: string;
}

export function DetailField({ label, value, className }: DetailFieldProps) {
  return (
    <div className={cn("mb-3", className)}>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-slate-200">{value}</dd>
    </div>
  );
}
