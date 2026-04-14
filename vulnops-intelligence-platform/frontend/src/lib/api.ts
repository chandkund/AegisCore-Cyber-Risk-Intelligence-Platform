import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./auth-storage";
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
} from "@/types/api";

function apiBase(): string {
  const b = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  return b.replace(/\/$/, "");
}

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${apiBase()}${p}`;
}

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const rt = getRefreshToken();
  if (!rt) return null;
  const res = await fetch(apiUrl("/api/v1/auth/refresh"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: rt }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const data = (await res.json()) as TokenResponse;
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  retried = false
): Promise<{ ok: boolean; status: number; data: T | null; error?: string }> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!headers.has("Content-Type") && init.body && typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(apiUrl(path), { ...init, headers });

  if (res.status === 401 && !retried && getRefreshToken()) {
    if (!refreshPromise) refreshPromise = refreshAccessToken();
    const newTok = await refreshPromise;
    refreshPromise = null;
    if (newTok) return apiFetch<T>(path, init, true);
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

export async function loginRequest(
  email: string,
  password: string
): Promise<{ ok: boolean; error?: string; tokens?: TokenResponse }> {
  const url = apiUrl("/api/v1/auth/login");
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const text = await res.text();
    const data = text
      ? (JSON.parse(text) as TokenResponse & { detail?: unknown })
      : null;
    if (!res.ok) {
      return { ok: false, error: formatApiDetail(data?.detail ?? "Login failed") };
    }
    return { ok: true, tokens: data as TokenResponse };
  } catch (err) {
    return { ok: false, error: "Network error: " + String(err) };
  }
}

export async function meRequest(): Promise<MeResponse | null> {
  const r = await apiFetch<MeResponse>("/api/v1/auth/me", { method: "GET" });
  if (!r.ok || !r.data) return null;
  return r.data;
}

export async function logoutRequest(): Promise<void> {
  const rt = getRefreshToken();
  if (rt) {
    await fetch(apiUrl("/api/v1/auth/logout"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
  }
  clearTokens();
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
