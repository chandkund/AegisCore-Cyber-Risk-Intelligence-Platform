// Compliance & Security Dashboard APIs (Platform Owner Only)
// These functions are separated from the main api.ts to reduce bundle size

import { apiUrl } from "./api";

/** Default fetch options for cookie-based auth */
const defaultFetchOptions: RequestInit = {
  credentials: "include", // Send cookies with every request
};

export interface SecurityScore {
  overall_score: number;
  max_score: number;
  grade: string;
  last_updated: string;
  details: Array<{
    category: string;
    score: number;
    max_score: number;
    status: "pass" | "warn" | "fail";
    findings: string[];
  }>;
}

export interface SecurityEvents {
  period: string;
  total_events: number;
  critical_events: number;
  failed_logins: number;
  blocked_requests: number;
  mfa_enrollments: number;
}

export interface ComplianceFramework {
  framework: string;
  readiness: "ready" | "in_progress" | "not_applicable";
  completion_percentage: number;
  gaps: string[];
  last_assessment: string | null;
}

export async function platformGetSecurityScore(): Promise<SecurityScore> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/platform/compliance/security-score"), {
    ...defaultFetchOptions,
    method: "GET",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get security score" }));
    throw new Error(error.detail || "Failed to get security score");
  }

  return response.json();
}

export async function platformGetSecurityEvents(periodDays: number = 7): Promise<SecurityEvents> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(
    apiUrl(`/api/v1/platform/compliance/security-events?period_days=${periodDays}`),
    {
      ...defaultFetchOptions,
      method: "GET",
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get security events" }));
    throw new Error(error.detail || "Failed to get security events");
  }

  return response.json();
}

export async function platformGetComplianceFrameworks(): Promise<ComplianceFramework[]> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/platform/compliance/frameworks"), {
    ...defaultFetchOptions,
    method: "GET",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get frameworks" }));
    throw new Error(error.detail || "Failed to get compliance frameworks");
  }

  return response.json();
}

export async function platformRecalculateCompliance(): Promise<{
  success: boolean;
  message: string;
  new_score: number;
  grade: string;
}> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/platform/compliance/recalculate"), {
    ...defaultFetchOptions,
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to recalculate" }));
    throw new Error(error.detail || "Failed to recalculate compliance");
  }

  return response.json();
}
