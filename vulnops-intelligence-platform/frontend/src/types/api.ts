export type MeResponse = {
  id: string;
  tenant_id: string;
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

export type RiskFactors = {
  cvss: number;
  criticality: number;
  exposure: number;
  exploit: number;
  age: number;
  ml_probability?: number | null;
};

export type RiskScoreOut = {
  finding_id: string;
  risk_score: number;
  rule_based_score: number;
  ml_score: number | null;
  calculation_method: string;
  factors: RiskFactors;
  contributing_factors: Array<{
    factor: string;
    weight: number;
    score: number;
    description: string;
    impact: string;
  }>;
  percentile_rank: number | null;
  calculated_at: string;
};

export type PrioritizedFindingOut = {
  id: string;
  asset_id: string;
  cve_record_id: string;
  cve_id: string | null;
  status: string;
  discovered_at: string;
  due_at: string | null;
  assigned_to_user_id: string | null;
  risk_score: number | null;
  risk_factors: Record<string, unknown> | null;
  risk_calculated_at: string | null;
  asset_name: string | null;
  asset_criticality: number | null;
  cvss_score: number | null;
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
  // Risk prioritization fields
  risk_score: number | null;
  risk_factors: Record<string, unknown> | null;
  risk_calculated_at: string | null;
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

export type RiskTrendPoint = {
  date: string;
  opened_count: number;
  avg_risk_score: number | null;
};

export type RiskTrendResponse = {
  days: number;
  points: RiskTrendPoint[];
};

export type SlaForecastResponse = {
  overdue_now: number;
  due_next_7_days: number;
  due_next_14_days: number;
  resolved_last_14_days: number;
  projected_daily_resolve_rate: number;
  predicted_breaches_next_7_days: number;
  predicted_breaches_next_14_days: number;
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

// Explanation types
export type RiskExplanationOut = {
  finding_id: string;
  risk_score: number;
  severity_level: string;
  overall_assessment: string;
  top_factors: Array<{
    factor: string;
    weight: number;
    score: number;
    description: string;
    impact: string;
  }>;
  detailed_explanation: string;
  remediation_priority_reason: string;
  comparable_examples: string[];
  generated_at: string;
};

// Search types
export type SearchResultItem = {
  finding_id: string;
  cve_id: string | null;
  title: string | null;
  asset_name: string;
  status: string;
  risk_score: number | null;
  relevance_score: number;
  semantic_score: number;
  keyword_score: number;
  match_type: string;
  snippet: string | null;
};

export type SearchResultOut = {
  query: string;
  total: number;
  limit: number;
  offset: number;
  results: SearchResultItem[];
};

// Simulation types
export type RiskMetrics = {
  total_count: number;
  average_risk_score: number;
  weighted_risk_score: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
};

export type ImpactedAsset = {
  asset_id: string;
  asset_name: string;
  criticality: number;
  findings_remediated: number;
  avg_risk_score: number | null;
};

export type RemainingRisk = {
  finding_id: string;
  cve_id: string | null;
  asset_name: string;
  risk_score: number;
};

export type SimulationResultOut = {
  scenario_name: string;
  selected_count: number;
  before_risk: RiskMetrics;
  after_risk: RiskMetrics;
  reduction_percentage: number;
  impacted_assets: ImpactedAsset[];
  remaining_top_risks: RemainingRisk[];
};

export type RecommendationItem = {
  finding_id: string;
  cve_id: string | null;
  asset_name: string;
  asset_id: string;
  risk_score: number;
  impact_score: number;
  reasoning: string;
};

// Assistant types
export type AssistantResponseOut = {
  answer: string;
  question_type: string;
  supporting_records: Record<string, unknown>[];
  confidence: string;
  suggested_followups: string[];
  generated_at: string;
};

export type TicketProvider = "github" | "jira" | "servicenow";

export type TicketOut = {
  id: string;
  finding_id: string;
  provider: TicketProvider;
  external_ticket_id: string;
  external_url: string | null;
  status: string;
  title: string;
  payload: Record<string, unknown> | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type BlastRadiusNode = {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  criticality: number;
  is_external: boolean;
  open_findings: number;
  high_risk_findings: number;
  max_risk_score: number | null;
};

export type BlastRadiusEdge = {
  source_asset_id: string;
  target_asset_id: string;
  dependency_type: string;
  trust_level: string;
  lateral_movement_score: number | null;
};

export type BlastRadiusResponse = {
  start_asset_id: string;
  max_depth: number;
  total_impacted_assets: number;
  internet_exposed_assets: number;
  high_risk_findings_in_radius: number;
  nodes: BlastRadiusNode[];
  edges: BlastRadiusEdge[];
};

export type ConnectorProvider = "nessus" | "qualys" | "defender" | "crowdstrike" | "wiz";

export type ConnectorIngestResponse = {
  provider: ConnectorProvider;
  received_records: number;
  normalized_records: number;
  deduplicated_records: number;
  created_assets: number;
  created_cves: number;
  created_findings: number;
  updated_findings: number;
  source_confidence_avg: number;
  high_confidence_records: number;
  watermark_updated: boolean;
};

export type PolicyRuleOut = {
  id: string;
  name: string;
  description: string | null;
  conditions: Record<string, unknown>;
  action: string;
  severity: string;
  is_enabled: boolean;
  created_at: string;
};

export type PolicyViolation = {
  policy_rule_id: string;
  policy_name: string;
  finding_id: string;
  action: string;
  severity: string;
  reason: string;
};

export type JobOut = {
  id: string;
  job_kind: string;
  status: string;
  payload: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ComplianceReportOut = {
  generated_at: string;
  total_open: number;
  overdue_count: number;
  avg_remediation_days: number;
  sla_breach_rate: number;
  policy_violations_count: number;
};

export type RootCauseCluster = {
  cluster_key: string;
  finding_count: number;
  top_assets: string[];
  representative_cves: string[];
};

export type SecretProviderStatus = {
  provider: string;
  configured: boolean;
  details: Record<string, string>;
};
