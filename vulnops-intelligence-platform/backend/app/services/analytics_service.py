from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    BusinessUnitRiskRow,
    SeverityCount,
    StatusCount,
    TopAssetRow,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.repo = AnalyticsRepository(db)

    def summary(self) -> AnalyticsSummary:
        total = self.repo.total_open()
        by_status = [StatusCount(status=s, count=c) for s, c in self.repo.summary_open_by_status()]
        by_sev = [
            SeverityCount(severity=s, count=c) for s, c in self.repo.summary_open_by_severity()
        ]
        return AnalyticsSummary(
            total_open_findings=total,
            by_status=by_status,
            by_severity=by_sev,
        )

    def top_assets(self, *, limit: int = 20) -> list[TopAssetRow]:
        rows = self.repo.top_assets_by_open_findings(limit=limit)
        return [TopAssetRow(**r) for r in rows]

    def business_units(self, *, limit: int = 50) -> list[BusinessUnitRiskRow]:
        rows = self.repo.business_unit_risk(limit=limit)
        return [BusinessUnitRiskRow(**r) for r in rows]
