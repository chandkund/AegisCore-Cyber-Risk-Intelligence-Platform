"use client";

import { cn } from "@/lib/utils";
import { useCallback, useEffect, useRef, useState } from "react";

interface OTPInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  disabled?: boolean;
  error?: string;
  label?: string;
}

export function OTPInput({
  length = 6,
  value,
  onChange,
  onComplete,
  disabled = false,
  error,
  label = "Enter verification code",
}: OTPInputProps) {
  const [focusedIndex, setFocusedIndex] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Ensure value is padded to length
  const paddedValue = value.padEnd(length, "").slice(0, length);
  const digits = paddedValue.split("");

  // Focus first input on mount
  useEffect(() => {
    if (!disabled && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [disabled]);

  const handleChange = useCallback(
    (index: number, inputValue: string) => {
      if (disabled) return;

      // Only allow single digit
      const digit = inputValue.slice(-1);
      if (!/^\d*$/.test(digit)) return;

      const newDigits = [...digits];
      newDigits[index] = digit;
      const newValue = newDigits.join("");
      onChange(newValue);

      // Auto-focus next input
      if (digit && index < length - 1) {
        inputRefs.current[index + 1]?.focus();
        setFocusedIndex(index + 1);
      }

      // Check if complete
      if (newValue.length === length && onComplete) {
        onComplete(newValue);
      }
    },
    [digits, disabled, length, onChange, onComplete]
  );

  const handleKeyDown = useCallback(
    (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (disabled) return;

      switch (e.key) {
        case "Backspace":
          e.preventDefault();
          if (digits[idx]) {
            // Clear current digit
            const newDigits = [...digits];
            newDigits[idx] = "";
            onChange(newDigits.join(""));
          } else if (idx > 0) {
            // Move to previous and clear it
            inputRefs.current[idx - 1]?.focus();
            setFocusedIndex(idx - 1);
            const newDigits = [...digits];
            newDigits[idx - 1] = "";
            onChange(newDigits.join(""));
          }
          break;

        case "ArrowLeft":
          e.preventDefault();
          if (idx > 0) {
            inputRefs.current[idx - 1]?.focus();
            setFocusedIndex(idx - 1);
          }
          break;

        case "ArrowRight":
          e.preventDefault();
          if (idx < length - 1) {
            inputRefs.current[idx + 1]?.focus();
            setFocusedIndex(idx + 1);
          }
          break;

        case "Enter":
          if (value.length === length && onComplete) {
            onComplete(value);
          }
          break;
      }
    },
    [digits, disabled, length, onChange, onComplete, value]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      e.preventDefault();
      if (disabled) return;

      const pastedData = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, length);
      onChange(pastedData);

      // Focus appropriate input
      const focusIndex = Math.min(pastedData.length, length - 1);
      inputRefs.current[focusIndex]?.focus();
      setFocusedIndex(focusIndex);

      if (pastedData.length === length && onComplete) {
        onComplete(pastedData);
      }
    },
    [disabled, length, onChange, onComplete]
  );

  const handleFocus = useCallback((index: number) => {
    setFocusedIndex(index);
    // Select all text for easy replacement
    inputRefs.current[index]?.select();
  }, []);

  return (
    <div className="flex flex-col gap-2">
      {label && (
        <label className="text-sm font-medium text-app-fg text-center">
          {label}
        </label>
      )}

      <div className="flex justify-center gap-2">
        {Array.from({ length }, (_, index) => (
          <input
            key={index}
            ref={(el) => {
              inputRefs.current[index] = el;
            }}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={1}
            value={digits[index] || ""}
            disabled={disabled}
            onChange={(e) => handleChange(index, e.target.value)}
            onKeyDown={(e) => handleKeyDown(index, e)}
            onPaste={handlePaste}
            onFocus={() => handleFocus(index)}
            className={cn(
              "w-12 h-14 text-center text-2xl font-bold rounded-lg border-2 bg-surface text-app-fg transition-all duration-200",
              "focus:outline-none focus:ring-2 focus:ring-accent/50",
              disabled && "opacity-50 cursor-not-allowed bg-slate-800",
              error
                ? "border-red-500 focus:border-red-500 focus:ring-red-500/50"
                : focusedIndex === index
                ? "border-accent"
                : digits[index]
                ? "border-green-500"
                : "border-app-border",
              digits[index] && !error && "bg-accent/10"
            )}
            aria-label={`Digit ${index + 1} of ${length}`}
          />
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-500 text-center" role="alert">
          {error}
        </p>
      )}

      <p className="text-xs text-slate-400 text-center">
        Enter the 6-digit code sent to your email
      </p>
    </div>
  );
}

interface EmailVerificationProps {
  email: string;
  onVerify: (code: string) => Promise<void>;
  onResend: () => Promise<void>;
  onCancel?: () => void;
  loading?: boolean;
  resendDisabled?: boolean;
  resendSeconds?: number;
  maxAttempts?: number;
  attempts?: number;
}

export function EmailVerificationDialog({
  email,
  onVerify,
  onResend,
  onCancel,
  loading = false,
  resendDisabled = false,
  resendSeconds = 0,
  maxAttempts = 5,
  attempts = 0,
}: EmailVerificationProps) {
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [verifying, setVerifying] = useState(false);

  const handleComplete = async (code: string) => {
    if (verifying || loading) return;

    setVerifying(true);
    setError(undefined);

    try {
      await onVerify(code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed");
      setOtp("");
    } finally {
      setVerifying(false);
    }
  };

  const handleResend = async () => {
    if (resendDisabled || loading) return;

    setError(undefined);
    setOtp("");

    try {
      await onResend();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resend code");
    }
  };

  const remainingAttempts = maxAttempts - attempts;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-md mx-auto">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-app-fg mb-2">
          Verify Your Email
        </h2>
        <p className="text-sm text-slate-400">
          We sent a verification code to
          <br />
          <span className="text-accent font-medium">{email}</span>
        </p>
      </div>

      <OTPInput
        value={otp}
        onChange={setOtp}
        onComplete={handleComplete}
        disabled={verifying || loading}
        error={error}
        label="Enter 6-digit code"
      />

      {attempts > 0 && (
        <p className="text-sm text-amber-500 text-center">
          {remainingAttempts} attempt{remainingAttempts !== 1 ? "s" : ""} remaining
        </p>
      )}

      <div className="flex flex-col gap-3">
        <button
          onClick={() => handleComplete(otp)}
          disabled={otp.length !== 6 || verifying || loading}
          className={cn(
            "w-full py-2 px-4 rounded-lg font-medium transition-colors",
            otp.length === 6 && !verifying && !loading
              ? "bg-accent hover:bg-accent/90 text-white"
              : "bg-slate-700 text-slate-400 cursor-not-allowed"
          )}
        >
          {verifying || loading ? "Verifying..." : "Verify Email"}
        </button>

        <div className="flex items-center justify-center gap-1 text-sm">
          <span className="text-slate-400">Didn&apos;t receive it?</span>
          <button
            onClick={handleResend}
            disabled={resendDisabled || loading}
            className={cn(
              "font-medium transition-colors",
              resendDisabled || loading
                ? "text-slate-500 cursor-not-allowed"
                : "text-accent hover:text-accent/80"
            )}
          >
            {resendDisabled
              ? `Resend in ${resendSeconds}s`
              : "Resend code"}
          </button>
        </div>

        {onCancel && (
          <button
            onClick={onCancel}
            className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
          >
            Skip for now
          </button>
        )}
      </div>
    </div>
  );
}
