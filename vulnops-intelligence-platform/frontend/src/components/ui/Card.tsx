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
        "app-panel",
        className
      )}
      aria-label={title || undefined}
    >
      {title ? (
        <h2 className="mb-3 text-lg font-semibold text-app-fg">{title}</h2>
      ) : null}
      {children}
    </section>
  );
}
