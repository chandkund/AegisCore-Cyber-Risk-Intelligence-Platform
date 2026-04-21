"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  Lock,
  Mail,
  Building2,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.25, 0.4, 0.25, 1],
    },
  },
};

const floatingLabelVariants = {
  initial: { y: 0, scale: 1 },
  focused: { y: -28, scale: 0.85, color: "#38bdf8" },
};

const glowVariants = {
  idle: {
    boxShadow: "0 0 0 0 rgba(56, 189, 248, 0)",
  },
  focused: {
    boxShadow: "0 0 20px 2px rgba(56, 189, 248, 0.3)",
  },
};

// Animated background particles
const ParticleBackground = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-1 h-1 bg-sky-400/20 rounded-full"
          initial={{
            x: Math.random() * 100 + "%",
            y: Math.random() * 100 + "%",
            scale: Math.random() * 0.5 + 0.5,
          }}
          animate={{
            y: [null, Math.random() * 100 + "%"],
            opacity: [0.2, 0.5, 0.2],
          }}
          transition={{
            duration: Math.random() * 10 + 10,
            repeat: Infinity,
            ease: "linear",
          }}
        />
      ))}
    </div>
  );
};

// Security badge component
const SecurityBadge = ({ icon: Icon, text }: { icon: any; text: string }) => (
  <motion.div
    className="flex items-center gap-2 text-slate-400 text-sm"
    initial={{ opacity: 0, x: -10 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: 0.5 }}
  >
    <div className="p-1.5 rounded-full bg-emerald-500/10">
      <Icon className="w-3.5 h-3.5 text-emerald-400" />
    </div>
    <span>{text}</span>
  </motion.div>
);

// Floating label input component
const FloatingInput = ({
  id,
  type,
  name,
  value,
  onChange,
  icon: Icon,
  label,
  error,
  showToggle,
  onToggle,
  isVisible,
}: {
  id: string;
  type: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  icon: any;
  label: string;
  error?: string;
  showToggle?: boolean;
  onToggle?: () => void;
  isVisible?: boolean;
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const hasValue = value.length > 0;

  return (
    <div className="relative">
      <motion.div
        className="relative group"
        variants={glowVariants}
        animate={isFocused ? "focused" : "idle"}
      >
        {/* Icon */}
        <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10">
          <Icon
            className={`w-5 h-5 transition-colors duration-300 ${
              isFocused ? "text-sky-400" : "text-slate-500"
            }`}
          />
        </div>

        {/* Input */}
        <input
          id={id}
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          className={`w-full h-14 pl-12 pr-${showToggle ? "12" : "4"} rounded-xl
            bg-slate-900/50 border-2 
            ${error ? "border-red-500/50" : "border-slate-700/50"}
            ${isFocused ? "border-sky-500/50" : ""}
            text-white placeholder-transparent
            transition-all duration-300 ease-out
            focus:outline-none focus:bg-slate-900/80
            backdrop-blur-sm`}
          placeholder={label}
        />

        {/* Floating Label */}
        <motion.label
          htmlFor={id}
          className={`absolute left-12 pointer-events-none font-medium
            ${hasValue || isFocused ? "text-sky-400 text-sm" : "text-slate-500 text-base"}`}
          initial={false}
          animate={{
            y: hasValue || isFocused ? -38 : -12,
            scale: hasValue || isFocused ? 0.85 : 1,
            color: isFocused ? "#38bdf8" : hasValue ? "#94a3b8" : "#64748b",
          }}
          transition={{ duration: 0.2, ease: "easeOut" }}
        >
          {label}
        </motion.label>

        {/* Password Toggle */}
        {showToggle && onToggle && (
          <button
            type="button"
            onClick={onToggle}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 
              hover:text-slate-300 transition-colors"
          >
            {isVisible ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}

        {/* Focus glow effect */}
        <motion.div
          className="absolute inset-0 rounded-xl pointer-events-none"
          initial={false}
          animate={{
            boxShadow: isFocused
              ? "0 0 0 2px rgba(56, 189, 248, 0.2), 0 0 20px rgba(56, 189, 248, 0.1)"
              : "0 0 0 0px rgba(56, 189, 248, 0)",
          }}
          transition={{ duration: 0.2 }}
        />
      </motion.div>

      {/* Error message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            className="flex items-center gap-1.5 mt-2 text-red-400 text-sm"
          >
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Main login page component
export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    companyCode: "",
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error when user types
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    const nextErrors: Record<string, string> = {};
    if (!formData.companyCode.trim()) nextErrors.companyCode = "Company code is required";
    if (!formData.email.trim()) nextErrors.email = "Email is required";
    if (!formData.password) nextErrors.password = "Password is required";
    if (Object.keys(nextErrors).length > 0) {
      setErrors(nextErrors);
      return;
    }
    setIsLoading(true);
    const result = await login(formData.companyCode.trim(), formData.email.trim(), formData.password);
    if (!result.ok) {
      setSubmitError(result.error || "Login failed");
      setIsLoading(false);
      return;
    }
    setIsLoading(false);
    router.replace("/dashboard");
  };

  return (
    <div className="min-h-screen bg-slate-950 flex overflow-hidden">
      {/* LEFT SIDE - Branding */}
      <motion.div
        className="hidden lg:flex lg:w-1/2 relative"
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: [0.25, 0.4, 0.25, 1] }}
      >
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-black" />

        {/* Animated particles */}
        <ParticleBackground />

        {/* Grid pattern overlay */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(56, 189, 248, 0.3) 1px, transparent 1px),
              linear-gradient(90deg, rgba(56, 189, 248, 0.3) 1px, transparent 1px)`,
            backgroundSize: "50px 50px",
          }}
        />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-center px-16 xl:px-24">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="visible"
          >
            {/* Logo */}
            <motion.div variants={itemVariants} className="mb-8">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="absolute inset-0 bg-sky-500 blur-xl opacity-50" />
                  <div className="relative p-3 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600">
                    <Shield className="w-8 h-8 text-white" />
                  </div>
                </div>
                <span className="text-2xl font-bold text-white tracking-tight">
                  AegisCore
                </span>
              </div>
            </motion.div>

            {/* Tagline */}
            <motion.h1
              variants={itemVariants}
              className="text-4xl xl:text-5xl font-bold text-white leading-tight mb-6"
            >
              Secure Intelligence
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-500">
                for Modern Enterprises
              </span>
            </motion.h1>

            {/* Description */}
            <motion.p
              variants={itemVariants}
              className="text-lg text-slate-400 max-w-md mb-12 leading-relaxed"
            >
              Advanced cybersecurity platform for vulnerability management, risk assessment, and threat intelligence.
            </motion.p>

            {/* Security badges */}
            <motion.div
              variants={itemVariants}
              className="flex flex-col gap-4"
            >
              <SecurityBadge icon={Lock} text="Enterprise-grade encryption" />
              <SecurityBadge icon={CheckCircle2} text="SOC 2 Type II certified" />
              <SecurityBadge icon={Sparkles} text="AI-powered threat detection" />
            </motion.div>
          </motion.div>
        </div>

        {/* Decorative gradient orb */}
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl" />
      </motion.div>

      {/* RIGHT SIDE - Login Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12 relative">
        {/* Subtle background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900/50 to-slate-950" />

        <motion.div
          className="relative w-full max-w-md"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.25, 0.4, 0.25, 1] }}
        >
          {/* Glass card */}
          <div className="relative">
            {/* Glow effect behind card */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-sky-500/20 to-blue-600/20 rounded-2xl blur opacity-50" />

            <div className="relative bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-800/50 p-8 lg:p-10 shadow-2xl">
              {/* Mobile logo (visible only on small screens) */}
              <div className="lg:hidden flex items-center gap-3 mb-8">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold text-white">AegisCore</span>
              </div>

              {/* Header */}
              <div className="mb-8">
                <motion.h2
                  className="text-2xl font-bold text-white mb-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                >
                  Welcome back
                </motion.h2>
                <motion.p
                  className="text-slate-400"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.5 }}
                >
                  Sign in to access your security dashboard
                </motion.p>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-6">
                <FloatingInput
                  id="companyCode"
                  type="text"
                  name="companyCode"
                  value={formData.companyCode}
                  onChange={handleChange}
                  icon={Building2}
                  label="Company Code"
                  error={errors.companyCode}
                />

                <FloatingInput
                  id="email"
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  icon={Mail}
                  label="Email address"
                  error={errors.email}
                />

                <FloatingInput
                  id="password"
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  icon={Lock}
                  label="Password"
                  error={errors.password}
                  showToggle
                  onToggle={() => setShowPassword(!showPassword)}
                  isVisible={showPassword}
                />

                {/* Forgot password link */}
                <div className="flex justify-end">
                  <Link
                    href="/forgot-password"
                    className="text-sm text-sky-400 hover:text-sky-300 transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>

                {/* Submit button */}
                <AnimatePresence>
                  {submitError && (
                    <motion.div
                      role="alert"
                      initial={{ opacity: 0, y: -6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -6 }}
                      className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300"
                    >
                      {submitError}
                    </motion.div>
                  )}
                </AnimatePresence>
                <motion.button
                  type="submit"
                  disabled={isLoading}
                  className="w-full relative group"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                >
                  {/* Button gradient background */}
                  <div className="absolute inset-0 bg-gradient-to-r from-sky-500 to-blue-600 rounded-xl opacity-100 group-hover:opacity-90 transition-opacity" />
                  
                  {/* Glow effect */}
                  <motion.div
                    className="absolute inset-0 bg-sky-400 rounded-xl blur opacity-0 group-hover:opacity-30 transition-opacity"
                    animate={isLoading ? { opacity: 0.3 } : {}}
                  />

                  <div className="relative h-14 flex items-center justify-center gap-2 text-white font-semibold">
                    {isLoading ? (
                      <>
                        <motion.div
                          className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        />
                        <span>Signing in...</span>
                      </>
                    ) : (
                      <>
                        <span>Sign in</span>
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </div>
                </motion.button>
              </form>

              {/* Divider */}
              <div className="relative my-8">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-800" />
                </div>
                <div className="relative flex justify-center">
                  <span className="px-4 bg-slate-900/80 text-slate-500 text-sm">
                    New to AegisCore?
                  </span>
                </div>
              </div>

              {/* Register link */}
              <Link href="/register">
                <motion.button
                  className="w-full h-12 flex items-center justify-center gap-2 
                    border-2 border-slate-700 rounded-xl text-slate-300 font-medium
                    hover:border-sky-500/50 hover:text-sky-400 transition-all duration-300"
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                >
                  Register your company
                </motion.button>
              </Link>

              {/* Trust footer */}
              <div className="mt-8 pt-6 border-t border-slate-800/50">
                <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" />
                    Encrypted authentication
                  </span>
                  <span className="w-1 h-1 rounded-full bg-slate-600" />
                  <span>SOC 2 certified</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
