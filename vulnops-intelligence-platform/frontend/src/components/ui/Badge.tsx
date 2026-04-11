import { cn } from "@/lib/utils";

const tones: Record<string, string> = {
  CRITICAL: "bg-rose-950 text-rose-200 ring-rose-800",
  HIGH: "bg-orange-950 text-orange-200 ring-orange-800",
  MEDIUM: "bg-amber-950 text-amber-200 ring-amber-800",
  LOW: "bg-emerald-950 text-emerald-200 ring-emerald-800",
  INFO: "bg-slate-700 text-slate-200 ring-slate-600",
  OPEN: "bg-sky-950 text-sky-200 ring-sky-800",
  IN_PROGRESS: "bg-violet-950 text-violet-200 ring-violet-800",
  REMEDIATED: "bg-emerald-950 text-emerald-200 ring-emerald-800",
};

export function Badge({ children, tone }: { children: string; tone?: string }) {
  const t = tone?.toUpperCase() || "";
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset",
        tones[t] || "bg-slate-800 text-slate-300 ring-slate-600"
      )}
    >
      {children}
    </span>
  );
}
