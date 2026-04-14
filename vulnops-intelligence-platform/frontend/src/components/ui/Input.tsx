import { cn } from "@/lib/utils";
import type { InputHTMLAttributes } from "react";

export function Input({
  className,
  id,
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label?: string }) {
  return (
    <div className="flex flex-col gap-1">
      {label ? (
        <label htmlFor={id} className="text-sm font-medium text-app-fg">
          {label}
        </label>
      ) : null}
      <input
        id={id}
        className={cn(
          "rounded-lg border border-app-border bg-surface px-3 py-2 text-app-fg placeholder:text-slate-500 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
          className
        )}
        {...props}
      />
    </div>
  );
}
