import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
};

export function Button({ className, variant = "primary", ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" &&
          "bg-accent text-white hover:bg-accent-hover focus-visible:ring-2 focus-visible:ring-accent",
        variant === "secondary" &&
          "border border-app-border bg-surface text-app-fg hover:bg-surface-muted",
        variant === "ghost" && "text-accent hover:bg-surface-muted",
        variant === "danger" && "bg-rose-700 text-white hover:bg-rose-600",
        className
      )}
      {...props}
    />
  );
}
