from __future__ import annotations

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
