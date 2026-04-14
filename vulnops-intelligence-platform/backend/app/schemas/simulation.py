"""Pydantic schemas for what-if risk simulation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    """Aggregate risk metrics."""
    total_count: int
    average_risk_score: float
    weighted_risk_score: float
    critical_count: int  # Risk >= 80
    high_count: int     # Risk >= 60
    medium_count: int   # Risk >= 40


class ImpactedAsset(BaseModel):
    """Asset impacted by simulated remediation."""
    asset_id: str
    asset_name: str
    criticality: int
    findings_remediated: int
    avg_risk_score: float | None


class RemainingRisk(BaseModel):
    """Top remaining risk after simulation."""
    finding_id: str
    cve_id: str | None
    asset_name: str
    risk_score: float


class SimulationRequest(BaseModel):
    """Request to simulate remediation scenario."""
    finding_ids: list[str] = Field(..., min_length=1, description="Vulnerability IDs to remediate")
    scenario_name: str | None = Field(None, description="Optional scenario name")


class SimulationResultOut(BaseModel):
    """Risk simulation result."""
    scenario_name: str
    selected_count: int
    before_risk: RiskMetrics
    after_risk: RiskMetrics
    reduction_percentage: float = Field(description="Risk reduction percentage")
    impacted_assets: list[ImpactedAsset]
    remaining_top_risks: list[RemainingRisk]


class ScenarioInput(BaseModel):
    """Single scenario for comparison."""
    name: str
    finding_ids: list[str] = Field(..., min_length=1)


class CompareScenariosRequest(BaseModel):
    """Request to compare multiple scenarios."""
    scenarios: list[ScenarioInput] = Field(..., min_length=2, max_length=5)


class RecommendationItem(BaseModel):
    """Single high-impact recommendation."""
    finding_id: str
    cve_id: str | None
    asset_name: str
    asset_id: str
    risk_score: float
    impact_score: float
    reasoning: str


class RecommendationsOut(BaseModel):
    """High-impact remediation recommendations."""
    recommendations: list[RecommendationItem]
    total_available: int
