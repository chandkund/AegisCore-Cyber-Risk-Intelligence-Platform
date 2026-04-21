"use client";

import { useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export interface ComplianceReport {
  total_findings: number;
  open_findings: number;
  overdue_findings: number;
  sla_breach_count: number;
  sla_breach_rate: number;
  mean_time_to_remediate_days: number | null;
  findings_by_severity: Record<string, number>;
  findings_by_status: Record<string, number>;
}

export interface RootCauseCluster {
  root_cause_category: string;
  count: number;
  percentage: number;
  example_cves: string[];
}

export interface SlaForecast {
  forecast_date: string;
  projected_open_count: number;
  projected_sla_breach_count: number;
  confidence: number;
}

export function useCompliance() {
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [clusters, setClusters] = useState<RootCauseCluster[]>([]);
  const [slaForecast, setSlaForecast] = useState<SlaForecast | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComplianceReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFetch<ComplianceReport>("/analytics/compliance-report");
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch compliance report");
      }
      
      setReport(response.data);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchRootCauseClusters = useCallback(async (limit: number = 10) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFetch<RootCauseCluster[]>(`/analytics/root-cause-clusters?limit=${limit}`);
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch root cause clusters");
      }
      
      setClusters(response.data);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSlaForecast = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFetch<{ forecast: SlaForecast }>("/analytics/sla-forecast");
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch SLA forecast");
      }
      
      setSlaForecast(response.data.forecast);
      return response.data.forecast;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      await Promise.all([
        fetchComplianceReport(),
        fetchRootCauseClusters(),
        fetchSlaForecast(),
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [fetchComplianceReport, fetchRootCauseClusters, fetchSlaForecast]);

  return {
    report,
    clusters,
    slaForecast,
    loading,
    error,
    fetchComplianceReport,
    fetchRootCauseClusters,
    fetchSlaForecast,
    loadAll,
  };
}
