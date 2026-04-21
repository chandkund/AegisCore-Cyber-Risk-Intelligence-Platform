"use client";

import { useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export interface Finding {
  id: string;
  asset_id: string;
  asset_name: string;
  vulnerability_id: string;
  cve_id: string | null;
  severity: string;
  cvss_score: number | null;
  status: string;
  discovered_at: string;
  last_seen_at: string | null;
  description: string | null;
  remediation: string | null;
  port: number | null;
  service_name: string | null;
  raw_payload: Record<string, unknown> | null;
  confidence: string | null;
  risk_score: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface FindingsFilters {
  severity?: string;
  status?: string;
  assetId?: string;
  search?: string;
}

export function useFindings() {
  const [data, setData] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);

  const fetchFindings = useCallback(async (
    limit: number = 50,
    offset: number = 0,
    filters: FindingsFilters = {}
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      params.set("limit", limit.toString());
      params.set("offset", offset.toString());
      
      if (filters.severity) {
        params.set("severity", filters.severity);
      }
      if (filters.status) {
        params.set("status", filters.status);
      }
      if (filters.assetId) {
        params.set("asset_id", filters.assetId);
      }
      if (filters.search) {
        params.set("search", filters.search);
      }
      
      const response = await apiFetch<PaginatedResponse<Finding>>(
        `/findings?${params.toString()}`
      );
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch findings");
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

  const fetchFindingDetail = useCallback(async (id: string): Promise<Finding | null> => {
    try {
      const response = await apiFetch<Finding>(`/findings/${id}`);
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch finding");
      }
      
      setSelectedFinding(response.data);
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
    selectedFinding,
    fetchFindings,
    fetchFindingDetail,
    setSelectedFinding,
  };
}
