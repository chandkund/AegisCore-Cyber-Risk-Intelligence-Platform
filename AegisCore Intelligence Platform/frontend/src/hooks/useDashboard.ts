"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

// Types matching backend schemas
export interface DashboardSummary {
  totalFindings: number;
  criticalFindings: number;
  highFindings: number;
  mediumFindings: number;
  lowFindings: number;
  assetsCount: number;
  openFindings: number;
  resolvedFindings: number;
  riskScore: number;
}

export interface TrendData {
  date: string;
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface SeverityDistribution {
  severity: string;
  count: number;
  percentage: number;
}

export interface ActivityItem {
  id: string;
  type: "finding_created" | "finding_updated" | "asset_added" | "scan_completed" | "remediation_applied";
  title: string;
  description: string;
  timestamp: string;
  severity?: string;
}

// API functions with error handling
async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiFetch<DashboardSummary>("/analytics/summary");
  if (!response.ok || !response.data) {
    throw new Error(response.error || "Failed to fetch dashboard summary");
  }
  return response.data;
}

async function fetchTrends(days: number = 30): Promise<TrendData[]> {
  const response = await apiFetch<TrendData[]>(`/analytics/trends?days=${days}`);
  if (!response.ok || !response.data) {
    throw new Error(response.error || "Failed to fetch trends");
  }
  return response.data;
}

async function fetchSeverityDistribution(): Promise<SeverityDistribution[]> {
  const response = await apiFetch<SeverityDistribution[]>("/analytics/severity-distribution");
  if (!response.ok || !response.data) {
    throw new Error(response.error || "Failed to fetch severity distribution");
  }
  return response.data;
}

async function fetchActivity(limit: number = 10): Promise<ActivityItem[]> {
  const response = await apiFetch<ActivityItem[]>(`/analytics/activity?limit=${limit}`);
  if (!response.ok || !response.data) {
    throw new Error(response.error || "Failed to fetch activity");
  }
  return response.data;
}

// React Query hooks
export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: fetchDashboardSummary,
    retry: 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useTrends(days: number = 30) {
  return useQuery({
    queryKey: ["dashboard", "trends", days],
    queryFn: () => fetchTrends(days),
    retry: 2,
    staleTime: 5 * 60 * 1000,
  });
}

export function useSeverityDistribution() {
  return useQuery({
    queryKey: ["dashboard", "severity-distribution"],
    queryFn: fetchSeverityDistribution,
    retry: 2,
    staleTime: 5 * 60 * 1000,
  });
}

export function useActivity(limit: number = 10) {
  return useQuery({
    queryKey: ["dashboard", "activity", limit],
    queryFn: () => fetchActivity(limit),
    retry: 2,
    staleTime: 60 * 1000, // 1 minute
  });
}
