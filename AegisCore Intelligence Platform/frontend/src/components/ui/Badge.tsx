import { cn } from "@/lib/utils";
import { HTMLAttributes } from "react";

// Legacy tone-based variants (for backward compatibility)
const tones: Record<string, string> = {
  CRITICAL: "bg-rose-500/15 text-rose-700 ring-rose-500/30",
  HIGH: "bg-orange-500/15 text-orange-700 ring-orange-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-700 ring-amber-500/30",
  LOW: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
  INFO: "bg-slate-500/20 text-slate-700 ring-slate-400/30",
  OPEN: "bg-sky-500/15 text-sky-700 ring-sky-500/30",
  IN_PROGRESS: "bg-violet-500/15 text-violet-700 ring-violet-500/30",
  REMEDIATED: "bg-emerald-500/15 text-emerald-700 ring-emerald-500/30",
};

// New shadcn/ui compatible variants
const variants: Record<string, string> = {
  default: "bg-primary text-primary-foreground hover:bg-primary/80",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/80",
  outline: "text-foreground border border-input bg-background hover:bg-accent hover:text-accent-foreground",
};

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: React.ReactNode;
  tone?: string;
  variant?: "default" | "secondary" | "destructive" | "outline";
}

export function Badge({ children, tone, variant = "default", className, ...props }: BadgeProps) {
  // If tone is provided, use legacy tone-based styling
  if (tone) {
    const t = tone.toUpperCase();
    return (
      <span
        className={cn(
          "inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
          tones[t] || "bg-gray-100 text-gray-700 ring-gray-300",
          className
        )}
        {...props}
      >
        {children}
      </span>
    );
  }

  // Otherwise use new variant-based styling
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium transition-colors",
        variants[variant] || variants.default,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
