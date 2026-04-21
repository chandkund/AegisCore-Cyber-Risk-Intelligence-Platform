import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md" | "lg";
};

export function Button({ className, variant = "primary", size = "md", ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" && "px-3 py-1.5 text-xs",
        size === "md" && "px-4 py-2 text-sm",
        size === "lg" && "px-5 py-2.5 text-base",
        variant === "primary" &&
          "bg-accent text-white hover:bg-accent-hover focus-visible:ring-2 focus-visible:ring-accent",
        variant === "secondary" &&
          "border border-app-border bg-surface text-app-fg hover:bg-surface-muted",
        variant === "ghost" && "text-accent hover:bg-surface-muted",
        variant === "danger" && "bg-rose-700 text-white hover:bg-rose-600",
        variant === "outline" && "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
        className
      )}
      {...props}
    />
  );
}
