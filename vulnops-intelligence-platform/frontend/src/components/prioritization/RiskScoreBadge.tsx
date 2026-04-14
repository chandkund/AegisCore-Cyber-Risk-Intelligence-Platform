"use client";

import React from "react";

interface RiskScoreBadgeProps {
  score: number | null | undefined;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

function getRiskColor(score: number): string {
  if (score >= 80) return "bg-red-600";      // Critical
  if (score >= 60) return "bg-orange-500";   // High
  if (score >= 40) return "bg-yellow-500"; // Medium
  if (score >= 20) return "bg-blue-500";     // Low
  return "bg-green-500";                     // Minimal
}

function getRiskLabel(score: number): string {
  if (score >= 80) return "Critical";
  if (score >= 60) return "High";
  if (score >= 40) return "Medium";
  if (score >= 20) return "Low";
  return "Minimal";
}

export function RiskScoreBadge({
  score,
  size = "md",
  showLabel = false,
}: RiskScoreBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
        Not scored
      </span>
    );
  }

  const sizeClasses = {
    sm: "w-8 h-8 text-xs",
    md: "w-12 h-12 text-sm",
    lg: "w-16 h-16 text-base",
  };

  const colorClass = getRiskColor(score);
  const label = getRiskLabel(score);

  return (
    <div className="flex items-center gap-2">
      <div
        className={`${sizeClasses[size]} ${colorClass} rounded-full flex items-center justify-center text-white font-bold shadow-sm`}
        title={`Risk Score: ${score.toFixed(1)} - ${label}`}
      >
        {score.toFixed(0)}
      </div>
      {showLabel && (
        <span className="text-sm font-medium text-gray-700">{label}</span>
      )}
    </div>
  );
}

export function RiskScoreBar({
  score,
  height = "h-2",
  showValue = true,
}: {
  score: number | null | undefined;
  height?: string;
  showValue?: boolean;
}) {
  if (score === null || score === undefined) {
    return <span className="text-xs text-gray-400">No score</span>;
  }

  const colorClass = getRiskColor(score);
  const percentage = Math.min(score, 100);

  return (
    <div className="w-full">
      <div className={`w-full ${height} bg-gray-200 rounded-full overflow-hidden`}>
        <div
          className={`${colorClass} ${height} rounded-full transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showValue && (
        <div className="flex justify-between mt-1 text-xs text-gray-500">
          <span>Risk: {score.toFixed(1)}/100</span>
          <span>{getRiskLabel(score)}</span>
        </div>
      )}
    </div>
  );
}
