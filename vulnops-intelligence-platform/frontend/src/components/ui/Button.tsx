import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
};

export function Button({ className, variant = "primary", ...props }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50",
        variant === "primary" &&
          "bg-sky-600 text-white hover:bg-sky-500 focus-visible:ring-2 focus-visible:ring-sky-400",
        variant === "secondary" &&
          "border border-slate-600 bg-slate-800 text-slate-100 hover:bg-slate-700",
        variant === "ghost" && "text-sky-400 hover:bg-slate-800/80",
        variant === "danger" && "bg-rose-700 text-white hover:bg-rose-600",
        className
      )}
      {...props}
    />
  );
}
