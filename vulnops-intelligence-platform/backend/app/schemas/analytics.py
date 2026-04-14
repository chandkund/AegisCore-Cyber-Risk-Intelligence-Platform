from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class SeverityCount(BaseModel):
    severity: str
    count: int


class AnalyticsSummary(BaseModel):
    total_open_findings: int
    by_status: list[StatusCount]
    by_severity: list[SeverityCount]


class TopAssetRow(BaseModel):
    asset_id: str
    asset_name: str
    open_findings: int
    max_cvss: float | None


class BusinessUnitRiskRow(BaseModel):
    business_unit_id: str
    business_unit_code: str
    business_unit_name: str
    open_findings: int
    critical_or_high: int


class RiskTrendPoint(BaseModel):
    date: date
    opened_count: int
    avg_risk_score: float | None


class RiskTrendResponse(BaseModel):
    days: int
    points: list[RiskTrendPoint]


class SlaForecastResponse(BaseModel):
    overdue_now: int
    due_next_7_days: int
    due_next_14_days: int
    resolved_last_14_days: int
    projected_daily_resolve_rate: float
    predicted_breaches_next_7_days: int
    predicted_breaches_next_14_days: int
