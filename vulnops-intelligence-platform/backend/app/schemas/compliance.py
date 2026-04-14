from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RootCauseCluster(BaseModel):
    cluster_key: str
    finding_count: int
    top_assets: list[str]
    representative_cves: list[str]


class ComplianceReportOut(BaseModel):
    generated_at: datetime
    total_open: int
    overdue_count: int
    avg_remediation_days: float
    sla_breach_rate: float
    policy_violations_count: int
