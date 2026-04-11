export type MeResponse = {
  id: string;
  email: string;
  full_name: string;
  roles: string[];
  is_active: boolean;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type FindingOut = {
  id: string;
  asset_id: string;
  cve_record_id: string;
  cve_id: string | null;
  status: string;
  discovered_at: string;
  remediated_at: string | null;
  due_at: string | null;
  assigned_to_user_id: string | null;
  internal_priority_score: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type AssetOut = {
  id: string;
  name: string;
  asset_type: string;
  hostname: string | null;
  ip_address: string | null;
  business_unit_id: string;
  team_id: string | null;
  location_id: string | null;
  criticality: number;
  owner_email: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AnalyticsSummary = {
  total_open_findings: number;
  by_status: { status: string; count: number }[];
  by_severity: { severity: string; count: number }[];
};

export type TopAssetRow = {
  asset_id: string;
  asset_name: string;
  open_findings: number;
  max_cvss: number | null;
};

export type BusinessUnitRiskRow = {
  business_unit_id: string;
  business_unit_code: string;
  business_unit_name: string;
  open_findings: number;
  critical_or_high: number;
};

export type MlModelInfoResponse = {
  inference_enabled: boolean;
  model_loaded: boolean;
  artifact_path: string;
  model_name?: string | null;
  model_version?: string | null;
  trained_at_utc?: string | null;
  metrics_holdout?: Record<string, unknown> | null;
  n_samples?: number | null;
};

export type MlPredictionResponse = {
  finding_id: string;
  probability_urgent: number;
  explain: { name: string; value: number }[];
  reference_time_utc: string;
};

export type UserOut = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
  roles: string[];
};

export type CveRecordOut = {
  id: string;
  cve_id: string;
  title: string | null;
  description: string | null;
  published_at: string | null;
  last_modified_at: string | null;
  cvss_base_score: string | null;
  cvss_vector: string | null;
  severity: string;
  epss_score: string | null;
  exploit_available: boolean;
};
