"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Shield,
  Mail,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Loader2,
} from "lucide-react";
import Link from "next/link";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Loading component for Suspense fallback
function VerifyEmailLoading() {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center">
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-sky-400 animate-spin mx-auto mb-4" />
        <p className="text-slate-400">Loading...</p>
      </div>
    </div>
  );
}

// Main component with search params
function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const userId = searchParams.get("userId");
  const email = searchParams.get("email");

  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(60);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Countdown timer for resend
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  // Handle input change
  const handleChange = (index: number, value: string) => {
    if (value.length > 1) {
      // Paste handling - fill all fields
      const digits = value.replace(/\D/g, "").split("").slice(0, 6);
      const newCode = [...code];
      digits.forEach((digit, i) => {
        if (i < 6) newCode[i] = digit;
      });
      setCode(newCode);
      // Focus last filled input or submit if complete
      const lastIndex = Math.min(digits.length, 5);
      inputRefs.current[lastIndex]?.focus();
      if (digits.length === 6) {
        handleVerify(newCode.join(""));
      }
      return;
    }

    // Single digit handling
    if (!/^\d*$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);
    setError(null);

    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit if complete
    if (index === 5 && value) {
      handleVerify(newCode.join(""));
    }
  };

  // Handle backspace
  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  // Verify code
  const handleVerify = async (fullCode?: string) => {
    const verifyCode = fullCode || code.join("");
    
    if (verifyCode.length !== 6) {
      setError("Please enter all 6 digits");
      return;
    }

    if (!userId) {
      setError("User ID not found. Please register again.");
      return;
    }

    setIsVerifying(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
          code: verifyCode,
        }),
        credentials: "include", // Include cookies
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Verification failed");
      }

      setSuccess(true);
      
      // Redirect to dashboard after short delay
      setTimeout(() => {
        router.push("/dashboard");
      }, 2000);
    } catch (error: any) {
      setError(error.message || "Invalid verification code");
      // Clear code on error
      setCode(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } finally {
      setIsVerifying(false);
    }
  };

  // Resend code
  const handleResend = async () => {
    if (!userId) {
      setError("User ID not found. Please register again.");
      return;
    }

    setIsResending(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/resend-verification`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to resend code");
      }

      setCountdown(60);
      setError(null);
    } catch (error: any) {
      setError(error.message || "Failed to resend code");
    } finally {
      setIsResending(false);
    }
  };

  // Focus first input on mount
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  if (!userId) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
        <div className="text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Invalid Access</h1>
          <p className="text-slate-400 mb-6">Please complete registration first.</p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-6 py-3 bg-sky-500 text-white rounded-xl font-medium hover:bg-sky-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Go to Registration
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex overflow-hidden">
      {/* Left side - branding */}
      <motion.div
        className="hidden lg:flex lg:w-1/2 relative"
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8 }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-black" />
        <div className="relative z-10 flex flex-col justify-center px-16 xl:px-24">
          <div className="flex items-center gap-3 mb-8">
            <div className="relative">
              <div className="absolute inset-0 bg-sky-500 blur-xl opacity-50" />
              <div className="relative p-3 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600">
                <Shield className="w-8 h-8 text-white" />
              </div>
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">AegisCore</span>
          </div>
          <h1 className="text-4xl xl:text-5xl font-bold text-white leading-tight mb-6">
            Verify your
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-500">
              email address
            </span>
          </h1>
          <p className="text-lg text-slate-400 max-w-md">
            We&apos;ve sent a 6-digit verification code to your email.
          </p>
        </div>
      </motion.div>

      {/* Right side - verification form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12">
        <motion.div
          className="w-full max-w-md"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
        >
          <div className="relative">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-sky-500/20 to-blue-600/20 rounded-2xl blur opacity-50" />
            
            <div className="relative bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-800/50 p-8 lg:p-10 shadow-2xl">
              {/* Success State */}
              <AnimatePresence>
                {success && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center py-8"
                  >
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", duration: 0.5 }}
                      className="w-20 h-20 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto mb-6"
                    >
                      <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                    </motion.div>
                    <h2 className="text-2xl font-bold text-white mb-2">Email Verified!</h2>
                    <p className="text-slate-400">Redirecting to your dashboard...</p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Verification Form */}
              {!success && (
                <>
                  <div className="text-center mb-8">
                    <div className="w-16 h-16 rounded-full bg-sky-500/20 flex items-center justify-center mx-auto mb-4">
                      <Mail className="w-8 h-8 text-sky-400" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Enter verification code</h2>
                    <p className="text-slate-400">
                      We sent a 6-digit code to{" "}
                      <span className="text-sky-400">{email || "your email"}</span>
                    </p>
                  </div>

                  {/* Error */}
                  <AnimatePresence>
                    {error && (
                      <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3"
                      >
                        <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                        <p className="text-red-400 text-sm">{error}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Code Input */}
                  <div className="flex justify-center gap-3 mb-8">
                    {code.map((digit, index) => (
                      <motion.input
                        key={index}
                        ref={(el) => { inputRefs.current[index] = el; }}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={(e) => handleChange(index, e.target.value)}
                        onKeyDown={(e) => handleKeyDown(index, e)}
                        disabled={isVerifying}
                        className="w-12 h-14 text-center text-2xl font-bold text-white bg-slate-900/50 
                          border-2 border-slate-700/50 rounded-xl focus:border-sky-500/50 
                          focus:outline-none transition-all disabled:opacity-50"
                        whileFocus={{ scale: 1.05 }}
                      />
                    ))}
                  </div>

                  {/* Verify Button */}
                  <motion.button
                    onClick={() => handleVerify()}
                    disabled={isVerifying || code.join("").length !== 6}
                    className="w-full h-14 flex items-center justify-center gap-2 
                      bg-gradient-to-r from-sky-500 to-blue-600 rounded-xl 
                      text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed
                      mb-6"
                    whileHover={{ scale: isVerifying ? 1 : 1.02 }}
                    whileTap={{ scale: isVerifying ? 1 : 0.98 }}
                  >
                    {isVerifying ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <>
                        <Shield className="w-5 h-5" />
                        Verify Email
                      </>
                    )}
                  </motion.button>

                  {/* Resend */}
                  <div className="text-center">
                    <p className="text-slate-400 text-sm mb-2">Didn&apos;t receive the code?</p>
                    {countdown > 0 ? (
                      <p className="text-slate-500 text-sm">
                        Resend in {countdown}s
                      </p>
                    ) : (
                      <motion.button
                        onClick={handleResend}
                        disabled={isResending}
                        className="inline-flex items-center gap-2 text-sky-400 hover:text-sky-300 
                          text-sm font-medium disabled:opacity-50"
                        whileHover={{ scale: 1.02 }}
                      >
                        {isResending ? (
                          <>
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            Sending...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-4 h-4" />
                            Resend code
                          </>
                        )}
                      </motion.button>
                    )}
                  </div>
                </>
              )}

              {/* Back to login */}
              <div className="mt-8 pt-6 border-t border-slate-800/50 text-center">
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 text-slate-400 hover:text-slate-300 text-sm"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Back to login
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

// Main export with Suspense boundary
export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<VerifyEmailLoading />}>
      <VerifyEmailContent />
    </Suspense>
  );
}
