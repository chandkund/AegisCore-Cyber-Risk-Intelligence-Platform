"""Pydantic schemas for risk explanations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RiskFactorExplanation(BaseModel):
    """Individual risk factor with explanation."""
    factor: str = Field(description="Factor type: cvss, criticality, exposure, exploit, age")
    weight: float = Field(description="Weight in scoring (0-1)")
    score: float = Field(description="Factor score (0-1)")
    description: str = Field(description="Human-readable description")
    impact: str = Field(description="impact level: high, medium, low")


class RiskExplanationOut(BaseModel):
    """Complete risk explanation for a vulnerability."""
    finding_id: str = Field(description="UUID of the vulnerability finding")
    risk_score: float = Field(ge=0, le=100, description="Risk score (0-100)")
    severity_level: str = Field(description="Critical, High, Medium, Low, or Minimal")
    overall_assessment: str = Field(description="High-level summary of risk")
    top_factors: list[dict[str, Any]] = Field(description="Top contributing factors")
    detailed_explanation: str = Field(description="Detailed breakdown of risk drivers")
    remediation_priority_reason: str = Field(description="Why this should be prioritized")
    comparable_examples: list[str] = Field(description="Comparable risk scenarios for context")
    generated_at: datetime = Field(description="When explanation was generated")


class TopFactorsOut(BaseModel):
    """Lightweight top factors response."""
    finding_id: str
    top_factors: list[dict[str, Any]]
