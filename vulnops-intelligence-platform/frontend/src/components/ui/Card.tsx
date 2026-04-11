import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

export function Card({
  children,
  className,
  title,
}: {
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg backdrop-blur-sm",
        className
      )}
      aria-label={title || undefined}
    >
      {title ? (
        <h2 className="mb-3 text-lg font-semibold text-slate-100">{title}</h2>
      ) : null}
      {children}
    </section>
  );
}
