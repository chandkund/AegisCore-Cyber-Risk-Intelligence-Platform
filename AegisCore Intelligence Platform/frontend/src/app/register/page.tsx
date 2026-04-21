"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Shield,
  Lock,
  Mail,
  Building2,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Check,
  X,
  Info,
  ShieldCheck,
  Fingerprint,
  Users,
} from "lucide-react";
import Link from "next/link";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ============================================
// TYPES & INTERFACES
// ============================================
interface FormData {
  companyName: string;
  companyCode: string;
  adminFullName: string;
  adminEmail: string;
  adminPassword: string;
  adminConfirmPassword: string;
  agreeToTerms: boolean;
}

interface PasswordStrength {
  score: number;
  label: string;
  color: string;
}

interface ValidationErrors {
  [key: string]: string;
}

// ============================================
// ANIMATION VARIANTS
// ============================================
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.25, 0.4, 0.25, 1] },
  },
};

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 300 : -300,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.4, ease: [0.25, 0.4, 0.25, 1] },
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 300 : -300,
    opacity: 0,
    transition: { duration: 0.3 },
  }),
};

const glowVariants = {
  idle: { boxShadow: "0 0 0 0 rgba(56, 189, 248, 0)" },
  focused: { boxShadow: "0 0 20px 2px rgba(56, 189, 248, 0.3)" },
};

// ============================================
// UTILITY COMPONENTS
// ============================================
const ParticleBackground = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {[...Array(15)].map((_, i) => (
      <motion.div
        key={i}
        className="absolute w-1 h-1 bg-sky-400/20 rounded-full"
        initial={{
          x: `${Math.random() * 100}%`,
          y: `${Math.random() * 100}%`,
          scale: Math.random() * 0.5 + 0.5,
        }}
        animate={{
          y: [null, `${Math.random() * 100}%`],
          opacity: [0.1, 0.4, 0.1],
        }}
        transition={{
          duration: Math.random() * 15 + 10,
          repeat: Infinity,
          ease: "linear",
        }}
      />
    ))}
  </div>
);

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

const StepIndicator = ({ currentStep, totalSteps }: { currentStep: number; totalSteps: number }) => (
  <div className="flex items-center gap-3 mb-8">
    {[...Array(totalSteps)].map((_, i) => (
      <div key={i} className="flex items-center gap-3">
        <motion.div
          className={`relative w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm
            ${i < currentStep ? "bg-emerald-500 text-white" : ""}
            ${i === currentStep ? "bg-sky-500 text-white" : ""}
            ${i > currentStep ? "bg-slate-800 text-slate-500 border border-slate-700" : ""}
          `}
          initial={false}
          animate={i === currentStep ? { scale: [1, 1.1, 1] } : {}}
          transition={{ duration: 0.3 }}
        >
          {i < currentStep ? (
            <Check className="w-5 h-5" />
          ) : (
            i + 1
          )}
          {i === currentStep && (
            <motion.div
              className="absolute inset-0 rounded-full bg-sky-500/30"
              animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          )}
        </motion.div>
        <span className={`text-sm font-medium ${i === currentStep ? "text-sky-400" : "text-slate-500"}`}>
          {i === 0 ? "Company" : i === 1 ? "Admin" : "Security"}
        </span>
        {i < totalSteps - 1 && (
          <div className={`w-8 h-0.5 ${i < currentStep ? "bg-emerald-500" : "bg-slate-800"}`} />
        )}
      </div>
    ))}
  </div>
);

// ============================================
// FORM INPUT COMPONENT
// ============================================
const FloatingInput = ({
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
  hint,
  autoComplete,
}: {
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
  hint?: string;
  autoComplete?: string;
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const hasValue = value.length > 0;
  const isFloating = hasValue || isFocused;

  return (
    <div className="relative mb-6">
      <motion.div
        className="relative group"
        variants={glowVariants}
        animate={isFocused ? "focused" : "idle"}
      >
        {/* Icon */}
        <div className="absolute left-4 top-1/2 -translate-y-1/2 z-10 pointer-events-none">
          <Icon
            className={`w-5 h-5 transition-colors duration-300 ${
              isFocused ? "text-sky-400" : "text-slate-500"
            }`}
          />
        </div>

        {/* Input */}
        <input
          type={type}
          name={name}
          id={name}
          value={value}
          onChange={onChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          autoComplete={autoComplete}
          className={`peer w-full h-14 pl-12 ${showToggle ? "pr-12" : "pr-4"} rounded-xl
            bg-slate-900/50 border-2 
            ${error ? "border-red-500/50" : "border-slate-700/50"}
            ${isFocused ? "border-sky-500/50" : ""}
            text-white placeholder-transparent
            transition-all duration-300 ease-out
            focus:outline-none focus:bg-slate-900/80
            backdrop-blur-sm text-base pt-4 pb-1`}
          placeholder=" "
        />

        {/* Floating Label - Using peer class for CSS-only floating label */}
        <label
          htmlFor={name}
          className={`absolute left-12 font-medium transition-all duration-200 ease-out pointer-events-none origin-left
            ${isFloating 
              ? "-top-1 text-xs text-sky-400 scale-90 -translate-y-0" 
              : "top-1/2 -translate-y-1/2 text-base text-slate-500 scale-100"
            }`}
        >
          {label}
        </label>

        {/* Password Toggle */}
        {showToggle && onToggle && (
          <button
            type="button"
            onClick={onToggle}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
          >
            {isVisible ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
          </button>
        )}

        {/* Focus Glow */}
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

      {/* Hint */}
      {hint && !error && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mt-2 text-xs text-slate-500 flex items-center gap-1"
        >
          <Info className="w-3 h-3" />
          {hint}
        </motion.p>
      )}

      {/* Error */}
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

// ============================================
// PASSWORD STRENGTH METER
// ============================================
const PasswordStrengthMeter = ({ password }: { password: string }) => {
  const getStrength = (pwd: string): PasswordStrength => {
    let score = 0;
    if (pwd.length >= 8) score++;
    if (pwd.match(/[a-z]/)) score++;
    if (pwd.match(/[A-Z]/)) score++;
    if (pwd.match(/[0-9]/)) score++;
    if (pwd.match(/[^a-zA-Z0-9]/)) score++;

    const levels: PasswordStrength[] = [
      { score: 0, label: "Too weak", color: "bg-red-500" },
      { score: 1, label: "Weak", color: "bg-red-500" },
      { score: 2, label: "Fair", color: "bg-yellow-500" },
      { score: 3, label: "Good", color: "bg-sky-500" },
      { score: 4, label: "Strong", color: "bg-emerald-500" },
      { score: 5, label: "Excellent", color: "bg-emerald-500" },
    ];

    return levels[score] || levels[0];
  };

  const strength = getStrength(password);
  const width = password.length > 0 ? `${(strength.score / 5) * 100}%` : "0%";

  if (password.length === 0) return null;

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400">Password strength</span>
        <span className={`text-xs font-medium ${strength.color.replace("bg-", "text-")}`}>
          {strength.label}
        </span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${strength.color} rounded-full`}
          initial={{ width: 0 }}
          animate={{ width }}
          transition={{ duration: 0.3 }}
        />
      </div>
      <div className="flex flex-wrap gap-2 mt-2">
        {[
          { text: "8+ chars", met: password.length >= 8 },
          { text: "Uppercase", met: /[A-Z]/.test(password) },
          { text: "Number", met: /[0-9]/.test(password) },
          { text: "Special", met: /[^a-zA-Z0-9]/.test(password) },
        ].map((req) => (
          <span
            key={req.text}
            className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 transition-colors
              ${req.met ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-800 text-slate-500"}`}
          >
            {req.met ? <Check className="w-3 h-3" /> : <X className="w-3 h-3" />}
            {req.text}
          </span>
        ))}
      </div>
    </div>
  );
};

// ============================================
// MAIN REGISTRATION PAGE
// ============================================
export default function RegisterPage() {
  const [step, setStep] = useState(0);
  const [direction, setDirection] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [companyCodeAvailable, setCompanyCodeAvailable] = useState<boolean | null>(null);

  const [formData, setFormData] = useState<FormData>({
    companyName: "",
    companyCode: "",
    adminFullName: "",
    adminEmail: "",
    adminPassword: "",
    adminConfirmPassword: "",
    agreeToTerms: false,
  });

  const [errors, setErrors] = useState<ValidationErrors>({});

  // Auto-generate company code from name
  useEffect(() => {
    if (formData.companyName && !formData.companyCode) {
      const suggested = formData.companyName
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "")
        .substring(0, 12);
      setFormData((prev) => ({ ...prev, companyCode: suggested }));
    }
  }, [formData.companyName]);

  // Check company code availability (simulated)
  useEffect(() => {
    if (formData.companyCode.length >= 3) {
      const timer = setTimeout(() => {
        // Simulate API check
        setCompanyCodeAvailable(formData.companyCode !== "taken");
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setCompanyCodeAvailable(null);
    }
  }, [formData.companyCode]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const validateStep = (currentStep: number): boolean => {
    const newErrors: ValidationErrors = {};

    if (currentStep === 0) {
      if (!formData.companyName.trim()) newErrors.companyName = "Company name is required";
      if (!formData.companyCode.trim()) newErrors.companyCode = "Company code is required";
      else if (formData.companyCode.length < 3) newErrors.companyCode = "Must be at least 3 characters";
    }

    if (currentStep === 1) {
      if (!formData.adminFullName.trim()) newErrors.adminFullName = "Full name is required";
      if (!formData.adminEmail.trim()) newErrors.adminEmail = "Email is required";
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.adminEmail)) {
        newErrors.adminEmail = "Please enter a valid email";
      }
    }

    if (currentStep === 2) {
      if (!formData.adminPassword) newErrors.adminPassword = "Password is required";
      else if (formData.adminPassword.length < 8) newErrors.adminPassword = "Must be at least 8 characters";
      if (formData.adminPassword !== formData.adminConfirmPassword) {
        newErrors.adminConfirmPassword = "Passwords do not match";
      }
      if (!formData.agreeToTerms) newErrors.agreeToTerms = "You must agree to the terms";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(step) && step < 2) {
      setDirection(1);
      setStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (step > 0) {
      setDirection(-1);
      setStep((prev) => prev - 1);
    }
  };

  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep(step)) return;

    // Only submit on final step
    if (step !== 2) {
      handleNext();
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/auth/register-company`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          company_name: formData.companyName,
          company_code: formData.companyCode,
          admin_email: formData.adminEmail,
          admin_password: formData.adminPassword,
          admin_full_name: formData.adminFullName,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed");
      }

      // Store user_id and redirect to verification
      setUserId(data.user_id);
      setRegistrationSuccess(true);
      
      // Redirect to verification page
      router.push(`/verify-email?userId=${data.user_id}&email=${encodeURIComponent(formData.adminEmail)}`);
    } catch (error: any) {
      setSubmitError(error.message || "An error occurred during registration");
    } finally {
      setIsSubmitting(false);
    }
  };

  const steps = [
    {
      title: "Company Details",
      description: "Set up your organization's workspace",
      fields: (
        <>
          <FloatingInput
            type="text"
            name="companyName"
            value={formData.companyName}
            onChange={handleChange}
            icon={Building2}
            label="Company Name"
            error={errors.companyName}
            hint="This will be displayed across your workspace"
            autoComplete="organization"
          />
          <div className="relative">
            <FloatingInput
              type="text"
              name="companyCode"
              value={formData.companyCode}
              onChange={handleChange}
              icon={Shield}
              label="Company Code"
              error={errors.companyCode}
              hint="Unique identifier for your company URL"
              autoComplete="off"
            />
            {companyCodeAvailable !== null && formData.companyCode.length >= 3 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`absolute right-4 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs font-medium
                  ${companyCodeAvailable ? "text-emerald-400" : "text-red-400"}`}
              >
                {companyCodeAvailable ? (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    Available
                  </>
                ) : (
                  <>
                    <X className="w-4 h-4" />
                    Taken
                  </>
                )}
              </motion.div>
            )}
          </div>
        </>
      ),
    },
    {
      title: "Admin Account",
      description: "Create your administrator profile",
      fields: (
        <>
          <FloatingInput
            type="text"
            name="adminFullName"
            value={formData.adminFullName}
            onChange={handleChange}
            icon={User}
            label="Full Name"
            error={errors.adminFullName}
            autoComplete="name"
          />
          <FloatingInput
            type="email"
            name="adminEmail"
            value={formData.adminEmail}
            onChange={handleChange}
            icon={Mail}
            label="Email Address"
            error={errors.adminEmail}
            hint="This will be your login email"
            autoComplete="email"
          />
        </>
      ),
    },
    {
      title: "Security Setup",
      description: "Secure your account with a strong password",
      fields: (
        <>
          <FloatingInput
            type={showPassword ? "text" : "password"}
            name="adminPassword"
            value={formData.adminPassword}
            onChange={handleChange}
            icon={Lock}
            label="Password"
            error={errors.adminPassword}
            showToggle
            onToggle={() => setShowPassword(!showPassword)}
            isVisible={showPassword}
            autoComplete="new-password"
          />
          <PasswordStrengthMeter password={formData.adminPassword} />
          <FloatingInput
            type={showConfirmPassword ? "text" : "password"}
            name="adminConfirmPassword"
            value={formData.adminConfirmPassword}
            onChange={handleChange}
            icon={CheckCircle2}
            label="Confirm Password"
            error={errors.adminConfirmPassword}
            showToggle
            onToggle={() => setShowConfirmPassword(!showConfirmPassword)}
            isVisible={showConfirmPassword}
            autoComplete="new-password"
          />
          {formData.adminConfirmPassword && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={`flex items-center gap-2 mb-4 text-sm
                ${formData.adminPassword === formData.adminConfirmPassword ? "text-emerald-400" : "text-red-400"}`}
            >
              {formData.adminPassword === formData.adminConfirmPassword ? (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  Passwords match
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4" />
                  Passwords do not match
                </>
              )}
            </motion.div>
          )}

          {/* Terms Checkbox */}
          <div className="mt-6">
            <label className="flex items-start gap-3 cursor-pointer group">
              <div className="relative">
                <input
                  type="checkbox"
                  name="agreeToTerms"
                  checked={formData.agreeToTerms}
                  onChange={handleChange}
                  className="sr-only peer"
                />
                <div className="w-5 h-5 rounded border-2 border-slate-600 peer-checked:bg-sky-500 peer-checked:border-sky-500 transition-all" />
                <Check className="w-3.5 h-3.5 text-white absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-0 peer-checked:opacity-100 transition-opacity" />
              </div>
              <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">
                I agree to the{" "}
                <Link href="/terms" className="text-sky-400 hover:text-sky-300">
                  Terms of Service
                </Link>{" "}
                and{" "}
                <Link href="/privacy" className="text-sky-400 hover:text-sky-300">
                  Privacy Policy
                </Link>
              </span>
            </label>
            {errors.agreeToTerms && (
              <p className="text-red-400 text-sm mt-2">{errors.agreeToTerms}</p>
            )}
          </div>
        </>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex overflow-hidden">
      {/* LEFT SIDE - Branding */}
      <motion.div
        className="hidden lg:flex lg:w-1/2 relative"
        initial={{ opacity: 0, x: -50 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, ease: [0.25, 0.4, 0.25, 1] }}
      >
        {/* Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-950 to-black" />
        <ParticleBackground />
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
          <motion.div variants={containerVariants} initial="hidden" animate="visible">
            {/* Logo */}
            <motion.div variants={itemVariants} className="mb-8">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className="absolute inset-0 bg-sky-500 blur-xl opacity-50" />
                  <div className="relative p-3 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600">
                    <Shield className="w-8 h-8 text-white" />
                  </div>
                </div>
                <span className="text-2xl font-bold text-white tracking-tight">AegisCore</span>
              </div>
            </motion.div>

            {/* Tagline */}
            <motion.h1
              variants={itemVariants}
              className="text-4xl xl:text-5xl font-bold text-white leading-tight mb-6"
            >
              Build your secure
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-blue-500">
                intelligence workspace
              </span>
            </motion.h1>

            {/* Description */}
            <motion.p
              variants={itemVariants}
              className="text-lg text-slate-400 max-w-md mb-12 leading-relaxed"
            >
              Join thousands of enterprises using AegisCore for advanced cybersecurity management.
            </motion.p>

            {/* Features */}
            <motion.div variants={itemVariants} className="flex flex-col gap-4">
              <SecurityBadge icon={ShieldCheck} text="Enterprise-grade security" />
              <SecurityBadge icon={Fingerprint} text="End-to-end encrypted authentication" />
              <SecurityBadge icon={Users} text="Team collaboration ready" />
              <SecurityBadge icon={Sparkles} text="AI-powered threat detection" />
            </motion.div>
          </motion.div>
        </div>

        {/* Decorative orbs */}
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl" />
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl" />
      </motion.div>

      {/* RIGHT SIDE - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900/50 to-slate-950" />

        <motion.div
          className="relative w-full max-w-md"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.25, 0.4, 0.25, 1] }}
        >
          <div className="relative">
            {/* Glow */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-sky-500/20 to-blue-600/20 rounded-2xl blur opacity-50" />

            <div className="relative bg-slate-900/80 backdrop-blur-xl rounded-2xl border border-slate-800/50 p-8 lg:p-10 shadow-2xl">
              {/* Mobile logo */}
              <div className="lg:hidden flex items-center gap-3 mb-6">
                <div className="p-2.5 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <span className="text-xl font-bold text-white">AegisCore</span>
              </div>

              {/* Step Indicator */}
              <StepIndicator currentStep={step} totalSteps={3} />

              {/* Header */}
              <div className="mb-6">
                <motion.h2
                  key={step}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-2xl font-bold text-white mb-1"
                >
                  {steps[step].title}
                </motion.h2>
                <motion.p
                  key={`desc-${step}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-slate-400"
                >
                  {steps[step].description}
                </motion.p>
              </div>

              {/* Submit Error */}
              <AnimatePresence>
                {submitError && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-3"
                  >
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-red-400 font-medium">Registration Failed</p>
                      <p className="text-red-400/80 text-sm">{submitError}</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Form Steps */}
              <form onSubmit={handleSubmit}>
                <AnimatePresence mode="wait" custom={direction}>
                  <motion.div
                    key={step}
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                  >
                    {steps[step].fields}
                  </motion.div>
                </AnimatePresence>

                {/* Navigation Buttons */}
                <div className="flex gap-3 mt-8">
                  {step > 0 && (
                    <motion.button
                      type="button"
                      onClick={handleBack}
                      className="h-12 px-6 flex items-center justify-center gap-2 
                        border-2 border-slate-700 rounded-xl text-slate-300 font-medium
                        hover:border-slate-600 hover:text-white transition-all duration-300"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <ArrowLeft className="w-4 h-4" />
                      Back
                    </motion.button>
                  )}

                  {step < 2 ? (
                    <motion.button
                      type="button"
                      onClick={handleNext}
                      className="flex-1 h-12 flex items-center justify-center gap-2 
                        bg-gradient-to-r from-sky-500 to-blue-600 rounded-xl 
                        text-white font-semibold hover:opacity-90 transition-all duration-300"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      Continue
                      <ArrowRight className="w-4 h-4" />
                    </motion.button>
                  ) : (
                    <motion.button
                      type="submit"
                      disabled={isSubmitting}
                      className="flex-1 h-12 flex items-center justify-center gap-2 
                        bg-gradient-to-r from-sky-500 to-blue-600 rounded-xl 
                        text-white font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                      whileHover={{ scale: isSubmitting ? 1 : 1.02 }}
                      whileTap={{ scale: isSubmitting ? 1 : 0.98 }}
                    >
                      {isSubmitting ? (
                        <motion.div
                          className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        />
                      ) : (
                        <>
                          <ShieldCheck className="w-5 h-5" />
                          Create Workspace
                        </>
                      )}
                    </motion.button>
                  )}
                </div>
              </form>

              {/* SSO Options */}
              {step === 0 && (
                <div className="mt-8">
                  <div className="relative mb-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-slate-800" />
                    </div>
                    <div className="relative flex justify-center">
                      <span className="px-4 bg-slate-900/80 text-slate-500 text-sm">
                        Or continue with
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {["Google", "Azure", "Okta"].map((provider) => (
                      <motion.button
                        key={provider}
                        type="button"
                        className="h-10 flex items-center justify-center gap-2 
                          border border-slate-700 rounded-lg text-slate-400 text-sm
                          hover:border-slate-600 hover:text-slate-300 transition-all"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        {provider}
                      </motion.button>
                    ))}
                  </div>
                </div>
              )}

              {/* Sign In Link */}
              <div className="mt-8 pt-6 border-t border-slate-800/50 text-center">
                <p className="text-slate-400">
                  Already have an account?{" "}
                  <Link href="/login" className="text-sky-400 hover:text-sky-300 font-medium">
                    Sign in
                  </Link>
                </p>
              </div>

              {/* Trust Footer */}
              <div className="mt-6 pt-4 border-t border-slate-800/50">
                <div className="flex items-center justify-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5" />
                    Encrypted
                  </span>
                  <span className="w-1 h-1 rounded-full bg-slate-600" />
                  <span>SOC 2</span>
                  <span className="w-1 h-1 rounded-full bg-slate-600" />
                  <span>GDPR</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
