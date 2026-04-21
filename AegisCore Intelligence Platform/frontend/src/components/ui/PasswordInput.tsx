"use client";

import { cn } from "@/lib/utils";
import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

interface PasswordInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string;
  showStrength?: boolean;
  strengthData?: {
    score: number;
    strength: string;
    label: string;
    color: string;
    suggestions: string[];
  } | null;
}

export function PasswordInput({
  className,
  id,
  label,
  showStrength = false,
  strengthData,
  ...props
}: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-col gap-1">
        {label ? (
          <label htmlFor={id} className="text-sm font-medium text-app-fg">
            {label}
          </label>
        ) : null}
        <div className="relative">
          <input
            id={id}
            type={showPassword ? "text" : "password"}
            className={cn(
              "w-full rounded-lg border border-app-border bg-surface px-3 py-2 pr-10 text-app-fg placeholder:text-slate-500 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
              className
            )}
            {...props}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-300 focus:outline-none focus:text-accent"
            tabIndex={-1}
            aria-label={showPassword ? "Hide secret text" : "Show secret text"}
          >
            {showPassword ? (
              <EyeOff className="h-5 w-5" />
            ) : (
              <Eye className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>

      {showStrength && strengthData && (
        <PasswordStrengthMeter data={strengthData} />
      )}
    </div>
  );
}

interface PasswordStrengthMeterProps {
  data: {
    score: number;
    strength: string;
    label: string;
    color: string;
    suggestions: string[];
  };
}

export function PasswordStrengthMeter({ data }: PasswordStrengthMeterProps) {
  const { score, label, color, suggestions } = data;

  // Calculate width percentage (0-100)
  const width = Math.min(100, Math.max(0, score));

  return (
    <div className="flex flex-col gap-1">
      {/* Strength bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full transition-all duration-300 ease-out"
            style={{
              width: `${width}%`,
              backgroundColor: color,
            }}
          />
        </div>
        <span
          className="text-xs font-medium"
          style={{ color }}
        >
          {label}
        </span>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <ul className="text-xs text-slate-400 mt-1 space-y-0.5">
          {suggestions.map((suggestion, index) => (
            <li key={index} className="flex items-start gap-1">
              <span className="text-accent">•</span>
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
