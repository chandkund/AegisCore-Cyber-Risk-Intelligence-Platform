/**
 * Cookie-Based API Client
 *
 * Authentication is handled via HTTPOnly cookies (secure, XSS-resistant).
 * - No tokens in JavaScript
 * - Cookies are sent automatically with credentials: 'include'
 * - Server sets HttpOnly, Secure, SameSite cookies
 */

import { clearSession, hasSession, setSessionActive } from "./auth-storage";
import { formatApiDetail } from "./api-errors";
import type {
  AnalyticsSummary,
  AssetOut,
  BlastRadiusResponse,
  BusinessUnitRiskRow,
  ComplianceReportOut,
  ConnectorIngestResponse,
  CveRecordOut,
  FindingOut,
  JobOut,
  MeResponse,
  MlModelInfoResponse,
  MlPredictionResponse,
  Paginated,
  PolicyRuleOut,
  PolicyViolation,
  RiskTrendResponse,
  RootCauseCluster,
  SecretProviderStatus,
  SlaForecastResponse,
  TicketOut,
  TokenResponse,
  TopAssetRow,
  UserInvitationOut,
} from "@/types/api";

function apiBase(): string {
  const b = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return b.replace(/\/$/, "");
}

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase()}${p}`;
}

/** Default fetch options for cookie-based auth */
const defaultFetchOptions: RequestInit = {
  credentials: "include", // Send cookies with every request
};

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  const res = await fetch(apiUrl("/api/v1/auth/refresh"), {
    ...defaultFetchOptions,
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    clearSession();
    return false;
  }
  return true;
}

/**
 * Make an authenticated API request using HTTPOnly cookies.
 * No Authorization header needed - cookies are sent automatically.
 */
export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  retried = false
): Promise<{ ok: boolean; status: number; data: T | null; error?: string }> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  // credentials: 'include' sends cookies automatically
  const res = await fetch(apiUrl(path), {
    ...defaultFetchOptions,
    ...init,
    headers,
  });

  // Handle 401 - try to refresh token automatically
  if (res.status === 401 && !retried) {
    if (!refreshPromise) refreshPromise = refreshAccessToken();
    const refreshed = await refreshPromise;
    refreshPromise = null;
    if (refreshed) return apiFetch<T>(path, init, true);
    // Refresh failed, clear session
    clearSession();
  }

  const text = await res.text();
  let data: T | null = null;
  if (text) {
    try {
      data = JSON.parse(text) as T;
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? (data as { detail: unknown }).detail
        : undefined;
    const err = formatApiDetail(detail ?? res.statusText);
    return { ok: false, status: res.status, data, error: err };
  }
  return { ok: true, status: res.status, data };
}

export interface LoginSuccess {
  user: MeResponse;
  csrf_token: string | null;
  expires_in: number;
  require_password_change: boolean;
}

export async function loginRequest(
  companyCode: string,
  email: string,
  password: string
): Promise<{ ok: boolean; error?: string; data?: LoginSuccess }> {
  const url = apiUrl("/api/v1/auth/login");
  try {
    const res = await fetch(url, {
      ...defaultFetchOptions,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_code: companyCode || null, email, password }),
    });
    const text = await res.text();
    const data = text
      ? (JSON.parse(text) as LoginSuccess & { detail?: unknown })
      : null;
    if (!res.ok) {
      return { ok: false, error: formatApiDetail(data?.detail ?? "Login failed") };
    }
    // Mark session as active (tokens are in cookies)
    setSessionActive();
    return { ok: true, data: data as LoginSuccess };
  } catch (err) {
    return { ok: false, error: "Network error: " + String(err) };
  }
}

export async function registerCompanyRequest(body: {
  company_name: string;
  company_code: string;
  admin_email: string;
  admin_password: string;
  admin_full_name: string;
}): Promise<{ ok: boolean; error?: string; tokens?: TokenResponse }> {
  const r = await apiFetch<TokenResponse>("/api/v1/auth/register-company", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!r.ok || !r.data) return { ok: false, error: r.error || "Registration failed" };
  return { ok: true, tokens: r.data };
}

export async function acceptInvitationRequest(body: {
  invitation_token: string;
  full_name: string;
  password: string;
}): Promise<{ ok: boolean; error?: string; tokens?: TokenResponse }> {
  const r = await apiFetch<TokenResponse>("/api/v1/auth/accept-invitation", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!r.ok || !r.data) return { ok: false, error: r.error || "Invitation acceptance failed" };
  return { ok: true, tokens: r.data };
}

export async function meRequest(): Promise<MeResponse | null> {
  const r = await apiFetch<MeResponse>("/api/v1/auth/me", { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function logoutRequest(): Promise<void> {
  // Send request with cookies - server will clear auth cookies
  await fetch(apiUrl("/api/v1/auth/logout"), {
    ...defaultFetchOptions,
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  // Clear local session state
  clearSession();
}

export async function createUserInvitation(body: {
  email: string;
  role_name: string;
  expires_in_hours?: number;
}): Promise<UserInvitationOut | null> {
  const r = await apiFetch<UserInvitationOut>("/api/v1/users/invitations", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function listFindings(params: {
  limit?: number;
  offset?: number;
  status?: string;
  q?: string;
  asset_id?: string;
  cve_id?: string;
}): Promise<Paginated<FindingOut> | null> {
  const sp = new URLSearchParams();
  if (params.limit != null) sp.set("limit", String(params.limit));
  if (params.offset != null) sp.set("offset", String(params.offset));
  if (params.status) sp.set("status", params.status);
  if (params.q) sp.set("q", params.q);
  if (params.asset_id) sp.set("asset_id", params.asset_id);
  if (params.cve_id) sp.set("cve_id", params.cve_id);
  const q = sp.toString();
  const path = `/api/v1/findings${q ? `?${q}` : ""}`;
  const r = await apiFetch<Paginated<FindingOut>>(path, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getFinding(id: string): Promise<FindingOut | null> {
  const r = await apiFetch<FindingOut>(`/api/v1/findings/${id}`, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function listAssets(params: {
  limit?: number;
  offset?: number;
}): Promise<Paginated<AssetOut> | null> {
  const sp = new URLSearchParams();
  if (params.limit != null) sp.set("limit", String(params.limit));
  if (params.offset != null) sp.set("offset", String(params.offset));
  const q = sp.toString();
  const path = `/api/v1/assets${q ? `?${q}` : ""}`;
  const r = await apiFetch<Paginated<AssetOut>>(path, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getAsset(id: string): Promise<AssetOut | null> {
  const r = await apiFetch<AssetOut>(`/api/v1/assets/${id}`, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getCveRecord(id: string): Promise<CveRecordOut | null> {
  const r = await apiFetch<CveRecordOut>(`/api/v1/cve-records/${id}`, {
    method: "GET",
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getAnalyticsSummary(): Promise<AnalyticsSummary | null> {
  const r = await apiFetch<AnalyticsSummary>("/api/v1/analytics/summary", {
    method: "GET",
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getTopAssets(): Promise<TopAssetRow[] | null> {
  const r = await apiFetch<TopAssetRow[]>("/api/v1/analytics/top-assets", {
    method: "GET",
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getBusinessUnitRisk(): Promise<BusinessUnitRiskRow[] | null> {
  const r = await apiFetch<BusinessUnitRiskRow[]>(
    "/api/v1/analytics/business-units",
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getMlModelInfo(): Promise<MlModelInfoResponse | null> {
  const r = await apiFetch<MlModelInfoResponse>("/api/v1/ml/model-info", {
    method: "GET",
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function predictFinding(
  findingId: string
): Promise<{ ok: true; data: MlPredictionResponse } | { ok: false; error: string; status: number }> {
  const r = await apiFetch<MlPredictionResponse>(
    `/api/v1/ml/predict/finding/${findingId}`,
    { method: "POST" }
  );
  if (!r.ok || !r.data) {
    return { ok: false, error: r.error || "Prediction failed", status: r.status };
  }
  return { ok: true, data: r.data };
}

// Prioritization API
import type { PrioritizedFindingOut, RiskScoreOut } from "@/types/api";

export async function getPrioritizedVulnerabilities(params: {
  limit?: number;
  offset?: number;
  min_risk_score?: number;
  status?: string;
  asset_id?: string;
  business_unit_id?: string;
}): Promise<Paginated<PrioritizedFindingOut> | null> {
  const sp = new URLSearchParams();
  if (params.limit != null) sp.set("limit", String(params.limit));
  if (params.offset != null) sp.set("offset", String(params.offset));
  if (params.min_risk_score != null) sp.set("min_risk_score", String(params.min_risk_score));
  if (params.status) sp.set("status", params.status);
  if (params.asset_id) sp.set("asset_id", params.asset_id);
  if (params.business_unit_id) sp.set("business_unit_id", params.business_unit_id);
  const q = sp.toString();
  const path = `/api/v1/prioritization/vulnerabilities${q ? `?${q}` : ""}`;
  const r = await apiFetch<Paginated<PrioritizedFindingOut>>(path, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getFindingRiskScore(
  findingId: string,
  includeMl = true
): Promise<RiskScoreOut | null> {
  const r = await apiFetch<RiskScoreOut>(
    `/api/v1/prioritization/vulnerabilities/${findingId}/risk-score?include_ml=${includeMl}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function recalculateFindingRisk(findingId: string): Promise<RiskScoreOut | null> {
  const r = await apiFetch<RiskScoreOut>(
    `/api/v1/prioritization/vulnerabilities/${findingId}/recalculate`,
    { method: "POST", body: JSON.stringify({ use_ml: true }) }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getTopRisks(limit = 10, minRiskScore = 50): Promise<PrioritizedFindingOut[] | null> {
  const r = await apiFetch<PrioritizedFindingOut[]>(
    `/api/v1/prioritization/top-risks?limit=${limit}&min_risk_score=${minRiskScore}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

// Explanation API
import type { RiskExplanationOut } from "@/types/api";

export async function getRiskExplanation(findingId: string): Promise<RiskExplanationOut | null> {
  const r = await apiFetch<RiskExplanationOut>(
    `/api/v1/explanations/vulnerabilities/${findingId}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getTopFactors(findingId: string): Promise<{ finding_id: string; top_factors: unknown[] } | null> {
  const r = await apiFetch<{ finding_id: string; top_factors: unknown[] }>(
    `/api/v1/explanations/vulnerabilities/${findingId}/factors`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

// Search API
import type { SearchResultOut, AssistantResponseOut, SimulationResultOut, RecommendationItem } from "@/types/api";

export async function searchVulnerabilities(
  query: string,
  params?: { limit?: number; offset?: number; status?: string; min_risk_score?: number }
): Promise<SearchResultOut | null> {
  const sp = new URLSearchParams();
  sp.set("q", query);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.offset !== undefined) sp.set("offset", String(params.offset));
  if (params?.status) sp.set("status", params.status);
  if (params?.min_risk_score) sp.set("min_risk_score", String(params.min_risk_score));
  
  const r = await apiFetch<SearchResultOut>(
    `/api/v1/search?${sp.toString()}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getSearchSuggestions(partial: string): Promise<string[] | null> {
  const r = await apiFetch<{ suggestions: string[] }>(
    `/api/v1/search/suggestions?q=${encodeURIComponent(partial)}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data.suggestions;
}

// Simulation API
export async function simulateRemediation(
  findingIds: string[],
  scenarioName?: string
): Promise<SimulationResultOut | null> {
  const r = await apiFetch<SimulationResultOut>(
    "/api/v1/simulate/remediation",
    {
      method: "POST",
      body: JSON.stringify({ finding_ids: findingIds, scenario_name: scenarioName }),
    }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getRemediationRecommendations(
  limit = 10,
  minRiskScore = 60
): Promise<{ recommendations: RecommendationItem[]; total_available: number } | null> {
  const r = await apiFetch<{ recommendations: RecommendationItem[]; total_available: number }>(
    `/api/v1/simulate/recommendations?limit=${limit}&min_risk_score=${minRiskScore}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

// Assistant API
export async function askAssistant(question: string): Promise<AssistantResponseOut | null> {
  const r = await apiFetch<AssistantResponseOut>(
    "/api/v1/assistant/query",
    {
      method: "POST",
      body: JSON.stringify({ question }),
    }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function quickAssistantQuery(question: string): Promise<{ answer: string; question_type: string } | null> {
  const r = await apiFetch<{ answer: string; question_type: string }>(
    "/api/v1/assistant/quick",
    {
      method: "POST",
      body: JSON.stringify({ question }),
    }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getRiskTrend(days = 30): Promise<RiskTrendResponse | null> {
  const r = await apiFetch<RiskTrendResponse>(`/api/v1/analytics/risk-trend?days=${days}`, {
    method: "GET",
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getSlaForecast(): Promise<SlaForecastResponse | null> {
  const r = await apiFetch<SlaForecastResponse>("/api/v1/analytics/sla-forecast", { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getRootCauseClusters(limit = 10): Promise<RootCauseCluster[] | null> {
  const r = await apiFetch<RootCauseCluster[]>(
    `/api/v1/analytics/root-cause-clusters?limit=${limit}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getComplianceReport(): Promise<ComplianceReportOut | null> {
  const r = await apiFetch<ComplianceReportOut>("/api/v1/analytics/compliance-report", {
    method: "GET",
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function createFindingTicket(
  findingId: string,
  body: {
    provider: "github" | "jira" | "servicenow";
    title: string;
    description: string;
    assignee?: string | null;
    labels?: string[];
    metadata?: Record<string, unknown>;
  }
): Promise<TicketOut | null> {
  const r = await apiFetch<TicketOut>(`/api/v1/tickets/findings/${findingId}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function listFindingTickets(findingId: string): Promise<TicketOut[] | null> {
  const r = await apiFetch<TicketOut[]>(`/api/v1/tickets/findings/${findingId}`, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getBlastRadiusForFinding(
  findingId: string,
  maxDepth = 3
): Promise<BlastRadiusResponse | null> {
  const r = await apiFetch<BlastRadiusResponse>(
    `/api/v1/attack-path/findings/${findingId}/blast-radius?max_depth=${maxDepth}`,
    { method: "GET" }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function ingestConnectorRecords(
  provider: "nessus" | "qualys" | "defender" | "crowdstrike" | "wiz",
  records: Array<Record<string, unknown>>,
  dryRun = true
): Promise<ConnectorIngestResponse | null> {
  const r = await apiFetch<ConnectorIngestResponse>(
    `/api/v1/ingestion/connectors/${provider}/ingest`,
    {
      method: "POST",
      body: JSON.stringify({ records, dry_run: dryRun }),
    }
  );
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function createPolicyRule(body: {
  name: string;
  description?: string;
  conditions: Record<string, unknown>;
  action?: string;
  severity?: string;
  is_enabled?: boolean;
}): Promise<PolicyRuleOut | null> {
  const r = await apiFetch<PolicyRuleOut>("/api/v1/policy/rules", {
    method: "POST",
    body: JSON.stringify(body),
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function listPolicyRules(): Promise<PolicyRuleOut[] | null> {
  const r = await apiFetch<PolicyRuleOut[]>("/api/v1/policy/rules", { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function evaluatePolicies(): Promise<PolicyViolation[] | null> {
  const r = await apiFetch<PolicyViolation[]>("/api/v1/policy/evaluate", { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function enqueueJob(
  jobKind: string,
  payload: Record<string, unknown> = {}
): Promise<JobOut | null> {
  const r = await apiFetch<JobOut>("/api/v1/jobs", {
    method: "POST",
    body: JSON.stringify({ job_kind: jobKind, payload }),
  });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function listJobs(limit = 50): Promise<JobOut[] | null> {
  const r = await apiFetch<JobOut[]>(`/api/v1/jobs?limit=${limit}`, { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function getSecretProviderStatus(): Promise<SecretProviderStatus | null> {
  const r = await apiFetch<SecretProviderStatus>("/api/v1/secrets/status", { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

// Platform Owner API Functions
export async function platformMetricsRequest(): Promise<{
  ok: boolean;
  data: import("@/types/api").PlatformMetricsOut | null;
  error?: string;
}> {
  return apiFetch<import("@/types/api").PlatformMetricsOut>("/api/v1/platform/metrics", { method: "GET" });
}

export async function platformTenantsRequest(
  limit = 50,
  offset = 0,
  approvalStatus?: string
): Promise<{
  ok: boolean;
  data: import("@/types/api").Paginated<import("@/types/api").TenantOut> | null;
  error?: string;
}> {
  let url = `/api/v1/platform/tenants?limit=${limit}&offset=${offset}`;
  if (approvalStatus) {
    url += `&approval_status=${approvalStatus}`;
  }
  return apiFetch<import("@/types/api").Paginated<import("@/types/api").TenantOut>>(url, { method: "GET" });
}

export async function platformTenantDetailRequest(
  tenantId: string
): Promise<{
  ok: boolean;
  data: import("@/types/api").TenantDetailOut | null;
  error?: string;
}> {
  return apiFetch<import("@/types/api").TenantDetailOut>(`/api/v1/platform/tenants/${tenantId}`, { method: "GET" });
}

export async function platformTenantAdminsRequest(
  tenantId: string
): Promise<{
  ok: boolean;
  data: import("@/types/api").TenantAdminOut[] | null;
  error?: string;
}> {
  return apiFetch<import("@/types/api").TenantAdminOut[]>(`/api/v1/platform/tenants/${tenantId}/admins`, { method: "GET" });
}

export async function platformUpdateTenantRequest(
  tenantId: string,
  body: import("@/types/api").TenantUpdate
): Promise<{
  ok: boolean;
  data: import("@/types/api").TenantOut | null;
  error?: string;
}> {
  return apiFetch<import("@/types/api").TenantOut>(`/api/v1/platform/tenants/${tenantId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function platformResetAdminPasswordRequest(
  tenantId: string,
  adminId: string,
  newPassword: string,
  requirePasswordChange = true
): Promise<{
  ok: boolean;
  error?: string;
}> {
  const r = await apiFetch<void>(`/api/v1/platform/tenants/${tenantId}/admins/${adminId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ new_password: newPassword, require_password_change: requirePasswordChange }),
  });
  return { ok: r.ok, error: r.error };
}

export async function platformCreateTenantRequest(
  body: {
    name: string;
    code: string;
    admin_email: string;
    admin_full_name: string;
    admin_password: string;
    approval_status?: string;
    is_active?: boolean;
  }
): Promise<{
  ok: boolean;
  data: import("@/types/api").TenantOut | null;
  error?: string;
}> {
  return apiFetch<import("@/types/api").TenantOut>("/api/v1/platform/tenants", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Platform Owner Upload Governance API Functions

export async function platformUploadsImportsRequest(
  limit = 50,
  offset = 0,
  uploadType?: string,
  status?: string
): Promise<{
  ok: boolean;
  data: {
    total: number;
    limit: number;
    offset: number;
    items: Array<{
      id: string;
      tenant_id: string;
      upload_type: string;
      original_filename: string;
      file_size_bytes: number;
      status: string;
      summary: {
        total_rows: number;
        inserted: number;
        updated: number;
        failed: number;
        skipped: number;
        errors: Array<{
          row_number: number;
          field?: string;
          message: string;
        }>;
      };
      processing_time_ms: number;
      uploaded_by_user_id: string | null;
      created_at: string;
      completed_at: string | null;
    }>;
  } | null;
  error?: string;
}> {
  let url = `/api/v1/platform/uploads/imports?limit=${limit}&offset=${offset}`;
  if (uploadType) {
    url += `&upload_type=${uploadType}`;
  }
  if (status) {
    url += `&status=${status}`;
  }
  return apiFetch(url, { method: "GET" });
}

export async function platformUploadsFilesRequest(
  limit = 50,
  offset = 0,
  uploadType?: string
): Promise<{
  ok: boolean;
  data: {
    total: number;
    limit: number;
    offset: number;
    total_storage_bytes: number;
    items: Array<{
      id: string;
      tenant_id: string;
      upload_type: string;
      original_filename: string;
      storage_path: string;
      file_size_bytes: number;
      mime_type: string;
      uploaded_by_user_id: string | null;
      created_at: string;
    }>;
  } | null;
  error?: string;
}> {
  let url = `/api/v1/platform/uploads/files?limit=${limit}&offset=${offset}`;
  if (uploadType) {
    url += `&upload_type=${uploadType}`;
  }
  return apiFetch(url, { method: "GET" });
}

export async function platformTenantUploadsRequest(
  tenantId: string,
  limit = 50,
  offset = 0
): Promise<{
  ok: boolean;
  data: {
    tenant_id: string;
    storage_bytes: number;
    imports: {
      total: number;
      items: Array<{
        id: string;
        upload_type: string;
        original_filename: string;
        status: string;
        summary: object;
        created_at: string;
      }>;
    };
    files: {
      total: number;
      items: Array<{
        id: string;
        upload_type: string;
        original_filename: string;
        file_size_bytes: number;
        created_at: string;
      }>;
    };
  } | null;
  error?: string;
}> {
  return apiFetch(`/api/v1/platform/tenants/${tenantId}/uploads?limit=${limit}&offset=${offset}`, { method: "GET" });
}

export async function platformStorageStatsRequest(): Promise<{
  ok: boolean;
  data: {
    total_storage_bytes: number;
    total_files: number;
    tenants: Array<{
      tenant_id: string;
      storage_bytes: number;
      file_count: number;
    }>;
  } | null;
  error?: string;
}> {
  return apiFetch("/api/v1/platform/storage/stats", { method: "GET" });
}

// Platform Owner Audit Logs API Functions

export async function platformAuditLogsRequest(
  limit = 50,
  offset = 0,
  filters?: {
    tenant_id?: string;
    action?: string;
    resource_type?: string;
    from_date?: string;
    to_date?: string;
  }
): Promise<{
  ok: boolean;
  data: {
    total: number;
    limit: number;
    offset: number;
    items: Array<{
      id: string;
      tenant_id: string | null;
      tenant_name: string | null;
      actor_user_id: string | null;
      actor_email: string | null;
      action: string;
      resource_type: string;
      resource_id: string | null;
      payload: object | null;
      occurred_at: string;
    }>;
  } | null;
  error?: string;
}> {
  let url = `/api/v1/platform/audit-logs?limit=${limit}&offset=${offset}`;
  if (filters?.tenant_id) {
    url += `&tenant_id=${filters.tenant_id}`;
  }
  if (filters?.action) {
    url += `&action=${filters.action}`;
  }
  if (filters?.resource_type) {
    url += `&resource_type=${filters.resource_type}`;
  }
  if (filters?.from_date) {
    url += `&from_date=${filters.from_date}`;
  }
  if (filters?.to_date) {
    url += `&to_date=${filters.to_date}`;
  }
  return apiFetch(url, { method: "GET" });
}

export async function platformAuditLogsSummaryRequest(
  days = 7
): Promise<{
  ok: boolean;
  data: {
    period_days: number;
    total_actions: number;
    actions_by_type: Array<{ action: string; count: number }>;
    actions_by_tenant: Array<{ tenant_id: string; count: number }>;
    daily_trend: Array<{ date: string; count: number }>;
  } | null;
  error?: string;
}> {
  return apiFetch(`/api/v1/platform/audit-logs/summary?days=${days}`, { method: "GET" });
}

// Upload API Functions
export async function uploadAssetsCsv(file: File): Promise<{
  ok: boolean;
  data?: {
    success: boolean;
    message: string;
    summary: {
      total_rows: number;
      inserted: number;
      updated: number;
      failed: number;
      skipped: number;
      errors: Array<{
        row_number: number;
        field?: string;
        message: string;
      }>;
      processing_time_ms: number;
    };
    import_id: string;
  };
  error?: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  // Cookie-based auth - no Authorization header needed
  try {
    const response = await fetch(apiUrl("/api/v1/upload/assets"), {
      ...defaultFetchOptions,
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
      return { ok: false, error: errorData.detail || `HTTP ${response.status}` };
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function uploadVulnerabilitiesCsv(file: File): Promise<{
  ok: boolean;
  data?: {
    success: boolean;
    message: string;
    summary: {
      total_rows: number;
      inserted: number;
      updated: number;
      failed: number;
      skipped: number;
      errors: Array<{
        row_number: number;
        field?: string;
        message: string;
      }>;
      processing_time_ms: number;
    };
    import_id: string;
  };
  error?: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  // Cookie-based auth - no Authorization header needed
  try {
    const response = await fetch(apiUrl("/api/v1/upload/vulnerabilities"), {
      ...defaultFetchOptions,
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: "Upload failed" }));
      return { ok: false, error: errorData.detail || `HTTP ${response.status}` };
    }

    const data = await response.json();
    return { ok: true, data };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "Network error" };
  }
}

export async function getUploadTemplate(type: "assets" | "vulnerabilities"): Promise<Blob> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl(`/api/v1/upload/templates/${type}`), {
    ...defaultFetchOptions,
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Failed to download template: ${response.status}`);
  }

  return response.blob();
}

// ============================================================================
// Password Validation APIs
// ============================================================================

export interface PasswordValidationResult {
  is_valid: boolean;
  strength: "weak" | "medium" | "strong";
  score: number;
  errors: string[];
  suggestions: string[];
  label: string;
  color: string;
  min_length: number;
  max_length: number;
}

export async function validatePasswordStrength(
  password: string,
  email?: string,
  name?: string
): Promise<PasswordValidationResult> {
  const response = await fetch(apiUrl("/api/v1/auth/validate-password"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password, email, name }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Validation failed" }));
    throw new Error(error.detail || "Password validation failed");
  }

  return response.json();
}

// ============================================================================
// Email Verification OTP APIs
// ============================================================================

export interface VerificationStatus {
  verified: boolean;
  email: string | null;
  pending_otp: boolean;
  otp_expires_at: string | null;
  otp_attempts: number;
  otp_max_attempts: number;
  can_resend: boolean;
  resend_seconds_remaining: number;
}

export async function getVerificationStatus(): Promise<VerificationStatus> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/auth/verification-status"), {
    ...defaultFetchOptions,
    method: "GET",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get status" }));
    throw new Error(error.detail || "Failed to get verification status");
  }

  return response.json();
}

export interface OTPVerifyResponse {
  success: boolean;
  message: string;
  verified: boolean;
}

export async function verifyEmailOTP(code: string): Promise<OTPVerifyResponse> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/auth/verify-email"), {
    ...defaultFetchOptions,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Verification failed" }));
    throw new Error(error.detail || "OTP verification failed");
  }

  return response.json();
}

export interface OTPResendResponse {
  success: boolean;
  message: string;
  can_resend_at?: string | null;
}

export async function resendVerificationCode(): Promise<OTPResendResponse> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/auth/resend-verification"), {
    ...defaultFetchOptions,
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to resend" }));
    throw new Error(error.detail || "Failed to resend verification code");
  }

  return response.json();
}

export async function requestVerificationCode(): Promise<OTPResendResponse> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl("/api/v1/auth/request-verification"), {
    ...defaultFetchOptions,
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to request" }));
    throw new Error(error.detail || "Failed to request verification code");
  }

  return response.json();
}

// ============================================================================
// Upload APIs
// ============================================================================

export interface UploadResult {
  success: boolean;
  message: string;
  inserted: number;
  updated: number;
  failed: number;
  import_id?: string;
}

export async function uploadAssets(file: File): Promise<UploadResult> {
  // Cookie-based auth - no Authorization header needed
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(apiUrl("/api/v1/upload/assets"), {
    ...defaultFetchOptions,
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || "Asset upload failed");
  }

  const data = await response.json();
  return {
    success: data.success,
    message: data.message,
    inserted: data.summary?.inserted || 0,
    updated: data.summary?.updated || 0,
    failed: data.summary?.failed || 0,
    import_id: data.import_id,
  };
}

export async function uploadVulnerabilities(file: File): Promise<UploadResult> {
  // Cookie-based auth - no Authorization header needed
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(apiUrl("/api/v1/upload/vulnerabilities"), {
    ...defaultFetchOptions,
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || "Vulnerability upload failed");
  }

  const data = await response.json();
  return {
    success: data.success,
    message: data.message,
    inserted: data.summary?.inserted || 0,
    updated: data.summary?.updated || 0,
    failed: data.summary?.failed || 0,
    import_id: data.import_id,
  };
}

export async function uploadMappings(file: File): Promise<UploadResult> {
  // Cookie-based auth - no Authorization header needed
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(apiUrl("/api/v1/upload/mappings"), {
    ...defaultFetchOptions,
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(error.detail || "Mapping upload failed");
  }

  const data = await response.json();
  return {
    success: data.success,
    message: data.message,
    inserted: data.summary?.inserted || 0,
    updated: data.summary?.updated || 0,
    failed: data.summary?.failed || 0,
    import_id: data.import_id,
  };
}

export async function downloadTemplate(type: "assets" | "vulnerabilities" | "mappings"): Promise<Blob> {
  // Cookie-based auth - no Authorization header needed
  const response = await fetch(apiUrl(`/api/v1/upload/templates/${type}`), {
    ...defaultFetchOptions,
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Failed to download template: ${response.status}`);
  }

  return response.blob();
}
