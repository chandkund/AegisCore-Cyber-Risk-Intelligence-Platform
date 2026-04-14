"use client";

import React, { useEffect, useState } from "react";
import { getRiskExplanation } from "@/lib/api";
import type { RiskExplanationOut } from "@/types/api";
import { RiskScoreBadge } from "@/components/prioritization/RiskScoreBadge";

interface RiskExplanationPanelProps {
  findingId: string;
}

export function RiskExplanationPanel({ findingId }: RiskExplanationPanelProps) {
  const [explanation, setExplanation] = useState<RiskExplanationOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadExplanation() {
      try {
        setLoading(true);
        const data = await getRiskExplanation(findingId);
        if (data) {
          setExplanation(data);
        } else {
          setError("Failed to load risk explanation");
        }
      } catch (err) {
        setError("Error loading explanation");
      } finally {
        setLoading(false);
      }
    }

    loadExplanation();
  }, [findingId]);

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
        <div className="h-20 bg-gray-200 rounded" />
      </div>
    );
  }

  if (error || !explanation) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-700">
        {error || "No explanation available"}
      </div>
    );
  }

  const severityColors: Record<string, string> = {
    Critical: "text-red-600 bg-red-50",
    High: "text-orange-600 bg-orange-50",
    Medium: "text-yellow-600 bg-yellow-50",
    Low: "text-blue-600 bg-blue-50",
    Minimal: "text-green-600 bg-green-50",
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <RiskScoreBadge score={explanation.risk_score} size="lg" showLabel />
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Risk Explanation</h3>
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
            severityColors[explanation.severity_level] || "text-gray-600 bg-gray-100"
          }`}>
            {explanation.severity_level} Severity
          </span>
        </div>
      </div>

      {/* Overall Assessment */}
      <div>
        <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
          Overall Assessment
        </h4>
        <p className="text-gray-700 leading-relaxed">
          {explanation.overall_assessment}
        </p>
      </div>

      {/* Top Contributing Factors */}
      {explanation.top_factors.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">
            Top Contributing Factors
          </h4>
          <div className="space-y-2">
            {explanation.top_factors.map((factor, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg border-l-4 ${
                  factor.impact === "high"
                    ? "bg-red-50 border-red-500"
                    : factor.impact === "medium"
                    ? "bg-orange-50 border-orange-500"
                    : "bg-gray-50 border-gray-300"
                }`}
              >
                <div className="flex justify-between items-start">
                  <p className="text-sm text-gray-700">{factor.description}</p>
                  <span className="text-xs font-medium text-gray-500 ml-2">
                    {Math.round(factor.weight * 100)}% weight
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Explanation */}
      <div>
        <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
          Detailed Explanation
        </h4>
        <div className="text-gray-700 leading-relaxed whitespace-pre-line">
          {explanation.detailed_explanation}
        </div>
      </div>

      {/* Remediation Priority */}
      <div className="bg-blue-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-blue-800 uppercase tracking-wide mb-2">
          Remediation Priority
        </h4>
        <p className="text-blue-900 leading-relaxed">
          {explanation.remediation_priority_reason}
        </p>
      </div>

      {/* Comparable Examples */}
      {explanation.comparable_examples.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-2">
            Risk Context
          </h4>
          <ul className="space-y-2">
            {explanation.comparable_examples.map((example, idx) => (
              <li key={idx} className="text-sm text-gray-600 flex items-start gap-2">
                <span className="text-gray-400">•</span>
                {example}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="text-xs text-gray-400 pt-4 border-t">
        Generated at: {new Date(explanation.generated_at).toLocaleString()}
      </div>
    </div>
  );
}
