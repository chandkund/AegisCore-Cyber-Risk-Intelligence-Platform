"use client";

import { useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export interface Asset {
  id: string;
  business_unit_id: string;
  name: string;
  type: string;
  criticality: number;
  owner_email: string | null;
  tags: Record<string, string> | null;
  description: string | null;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
  ip_address: string | null;
  hostname: string | null;
  os_family: string | null;
  cloud_provider: string | null;
  region: string | null;
  open_findings_count: number | null;
  max_risk_score: number | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface AssetsFilters {
  type?: string;
  criticality?: number;
  search?: string;
}

export function useAssets() {
  const [data, setData] = useState<Asset[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);

  const fetchAssets = useCallback(async (
    limit: number = 50,
    offset: number = 0,
    filters: AssetsFilters = {}
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      params.set("limit", limit.toString());
      params.set("offset", offset.toString());
      
      if (filters.type) {
        params.set("type", filters.type);
      }
      if (filters.criticality !== undefined) {
        params.set("criticality", filters.criticality.toString());
      }
      if (filters.search) {
        params.set("search", filters.search);
      }
      
      const response = await apiFetch<PaginatedResponse<Asset>>(
        `/assets?${params.toString()}`
      );
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch assets");
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

  const fetchAssetDetail = useCallback(async (id: string): Promise<Asset | null> => {
    try {
      const response = await apiFetch<Asset>(`/assets/${id}`);
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch asset");
      }
      
      setSelectedAsset(response.data);
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
    selectedAsset,
    fetchAssets,
    fetchAssetDetail,
    setSelectedAsset,
  };
}
