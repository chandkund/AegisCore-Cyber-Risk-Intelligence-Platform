import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./auth-storage";
import { formatApiDetail } from "./api-errors";
import type {
  AnalyticsSummary,
  AssetOut,
  BusinessUnitRiskRow,
  CveRecordOut,
  FindingOut,
  MeResponse,
  MlModelInfoResponse,
  MlPredictionResponse,
  Paginated,
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
  const res = await fetch(apiUrl("/api/v1/auth/login"), {
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
