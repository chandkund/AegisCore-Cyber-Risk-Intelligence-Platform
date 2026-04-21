"use client";

import { useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

// Types matching backend schemas
export interface PrioritizedVulnerability {
  id: string;
  asset_id: string;
  cve_record_id: string;
  cve_id: string;
  status: string;
  discovered_at: string;
  due_at: string | null;
  assigned_to_user_id: string | null;
  risk_score: number;
  risk_factors: Record<string, number>;
  risk_calculated_at: string | null;
  asset_name: string;
  asset_criticality: string;
  cvss_score: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface RiskScoreDetails {
  finding_id: string;
  risk_score: number;
  rule_based_score: number;
  ml_score: number | null;
  calculation_method: string;
  factors: {
    cvss: number;
    criticality: number;
    exposure: number;
    exploit: number;
    age: number;
    ml_probability: number | null;
  };
  contributing_factors: string[];
  percentile_rank: number;
  calculated_at: string;
}

export interface Filters {
  minRiskScore?: number;
  status?: string;
  assetId?: string;
  businessUnitId?: string;
}

export function useVulnerabilities() {
  const [data, setData] = useState<PrioritizedVulnerability[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchVulnerabilities = useCallback(async (
    limit: number = 50,
    offset: number = 0,
    filters: Filters = {}
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      params.set("limit", limit.toString());
      params.set("offset", offset.toString());
      
      if (filters.minRiskScore !== undefined) {
        params.set("min_risk_score", filters.minRiskScore.toString());
      }
      if (filters.status) {
        params.set("status", filters.status);
      }
      if (filters.assetId) {
        params.set("asset_id", filters.assetId);
      }
      if (filters.businessUnitId) {
        params.set("business_unit_id", filters.businessUnitId);
      }
      
      const response = await apiFetch<PaginatedResponse<PrioritizedVulnerability>>(
        `/prioritization/vulnerabilities?${params.toString()}`
      );
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch vulnerabilities");
      }
      
      setData(response.data.items);
      setTotal(response.data.total);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRiskScore = useCallback(async (findingId: string): Promise<RiskScoreDetails | null> => {
    try {
      const response = await apiFetch<RiskScoreDetails>(
        `/prioritization/vulnerabilities/${findingId}/risk-score`
      );
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch risk score");
      }
      
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    }
  }, []);

  return {
    data,
    total,
    loading,
    error,
    fetchVulnerabilities,
    fetchRiskScore,
  };
}
