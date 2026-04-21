"use client";

import { useState, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export interface Job {
  id: string;
  job_kind: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  payload: Record<string, unknown>;
  result?: Record<string, unknown> | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  actor_user_id: string;
}

export interface CreateJobRequest {
  job_kind: string;
  payload: Record<string, unknown>;
}

export function useJobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState(null);

  const fetchJobs = useCallback(async (limit: number = 50) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFetch<Job[]>(`/jobs?limit=${limit}`);
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to fetch jobs");
      }
      
      setJobs(response.data);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const enqueueJob = useCallback(async (jobKind: string, payload: Record<string, unknown>) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFetch<Job>("/jobs", {
        method: "POST",
        body: JSON.stringify({ job_kind: jobKind, payload }),
      });
      
      if (!response.ok || !response.data) {
        throw new Error(response.error || "Failed to enqueue job");
      }
      
      // Refresh jobs list
      await fetchJobs();
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : "An error occurred";
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [fetchJobs]);

  return {
    jobs,
    loading,
    error,
    fetchJobs,
    enqueueJob,
  };
}
