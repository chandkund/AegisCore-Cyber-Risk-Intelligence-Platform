"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Filter, X } from "lucide-react";
import { Button } from "./Button";

interface FilterBarProps {
  children: ReactNode;
  onClear?: () => void;
  hasFilters?: boolean;
  className?: string;
}

export function FilterBar({
  children,
  onClear,
  hasFilters = false,
  className,
}: FilterBarProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-3 rounded-xl border border-slate-700/50 bg-slate-800/50 p-4",
        className
      )}
    >
      <div className="flex items-center gap-2 text-slate-400">
        <Filter className="h-4 w-4" />
        <span className="text-sm font-medium">Filters</span>
      </div>
      
      <div className="flex flex-1 flex-wrap items-center gap-3">
        {children}
      </div>
      
      {hasFilters && onClear && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          className="gap-1 text-slate-400 hover:text-slate-200"
        >
          <X className="h-4 w-4" />
          Clear
        </Button>
      )}
    </div>
  );
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
  className?: string;
}

export function FilterSelect({
  label,
  value,
  options,
  onChange,
  className,
}: FilterSelectProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <label className="text-xs text-slate-500">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm",
          "text-slate-200 outline-none transition-colors",
          "focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20",
          "hover:border-slate-600"
        )}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

interface FilterSearchProps {
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function FilterSearch({
  placeholder = "Search...",
  value,
  onChange,
  className,
}: FilterSearchProps) {
  return (
    <div className={cn("relative", className)}>
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "w-full rounded-lg border border-slate-700 bg-slate-800 pl-9 pr-3 py-1.5 text-sm",
          "text-slate-200 placeholder:text-slate-500",
          "outline-none transition-colors",
          "focus:border-sky-500 focus:ring-1 focus:ring-sky-500/20",
          "hover:border-slate-600"
        )}
      />
      <svg
        className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      {value && (
        <button
          onClick={() => onChange("")}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
