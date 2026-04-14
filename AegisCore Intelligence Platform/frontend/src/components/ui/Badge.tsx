import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  CRITICAL: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
  HIGH: "bg-orange-500/15 text-orange-300 ring-orange-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  LOW: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  INFO: "bg-slate-500/20 text-slate-200 ring-slate-400/30",
  OPEN: "bg-sky-500/15 text-sky-300 ring-sky-500/30",
  IN_PROGRESS: "bg-violet-500/15 text-violet-300 ring-violet-500/30",
  REMEDIATED: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
};

export function Badge({ children, tone }: { children: string; tone?: string }) {
  const t = tone?.toUpperCase() || "";
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tones[t] || "bg-surface-muted text-app-fg ring-app-border"
      )}
    >
      {children}
    </span>
  );
}
