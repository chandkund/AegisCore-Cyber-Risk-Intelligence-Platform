"""Pydantic schemas for prioritization and risk scoring."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class RiskFactorDetail(BaseModel):
    """Individual risk factor score and description."""
    factor: str  # cvss, criticality, exposure, exploit, age, ml
    weight: float
    score: float
    description: str
    impact: str  # high, medium, low


class RiskFactorsOut(BaseModel):
    """All risk factor scores (0-1 scale)."""
    cvss: float = Field(ge=0, le=1)
    criticality: float = Field(ge=0, le=1)
    exposure: float = Field(ge=0, le=1)
    exploit: float = Field(ge=0, le=1)
    age: float = Field(ge=0, le=1)
    ml_probability: float | None = Field(None, ge=0, le=1)


class RiskScoreOut(BaseModel):
    """Detailed risk score response for a vulnerability."""
    finding_id: str
    risk_score: float = Field(ge=0, le=100, description="Final risk score (0-100)")
    rule_based_score: float = Field(ge=0, le=100)
    ml_score: float | None = Field(None, ge=0, le=100)
    calculation_method: str = Field(description="rule_based, ml, or hybrid")
    factors: RiskFactorsOut
    contributing_factors: list[dict[str, Any]] = Field(
        description="Top factors driving the risk score"
    )
    percentile_rank: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentile among all open vulnerabilities (100=highest risk)"
    )
    calculated_at: datetime


class PrioritizedFindingOut(BaseModel):
    """Vulnerability finding enriched with risk score for prioritization."""
    model_config = {"from_attributes": True}
    
    id: str
    asset_id: str
    cve_record_id: str
    cve_id: str | None
    status: str
    discovered_at: datetime
    due_at: datetime | None
    assigned_to_user_id: str | None
    
    # Risk scoring fields
    risk_score: float | None = Field(None, ge=0, le=100)
    risk_factors: dict[str, Any] | None
    risk_calculated_at: datetime | None
    
    # Enriched data
    asset_name: str | None
    asset_criticality: int | None
    cvss_score: float | None


class RiskRecalculateRequest(BaseModel):
    """Request to recalculate risk for a specific finding."""
    use_ml: bool = Field(
        default=True,
        description="Include ML prediction if model available"
    )


class BulkRecalculateRequest(BaseModel):
    """Request to bulk recalculate risk scores."""
    batch_size: int = Field(default=100, ge=10, le=500)
    use_ml: bool = Field(
        default=True,
        description="Include ML predictions if model available"
    )


class BulkRecalculateResponse(BaseModel):
    """Response from bulk risk recalculation."""
    total: int
    updated: int
    failed: int
    batch_size: int


class TopRiskFilter(BaseModel):
    """Filter parameters for top risks query."""
    min_risk_score: float = Field(default=50.0, ge=0, le=100)
    business_unit_id: str | None = None
    asset_type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class RiskTrendDataPoint(BaseModel):
    """Single data point for risk trend analysis."""
    date: datetime
    avg_risk_score: float
    high_risk_count: int  # Risk score >= 70
    critical_risk_count: int  # Risk score >= 85
    total_open: int


class RiskTrendResponse(BaseModel):
    """Risk trend over time for analytics."""
    business_unit_id: str | None
    asset_id: str | None
    period_days: int
    data_points: list[RiskTrendDataPoint]


class PrioritizationFeedbackRequest(BaseModel):
    feedback_type: str = Field(
        description="accepted_risk | fixed | false_positive | escalated | deferred"
    )
    notes: str | None = Field(default=None, max_length=2000)


class PrioritizationFeedbackResponse(BaseModel):
    feedback_id: str
    finding_id: str
    queued_retrain_job_id: str | None
