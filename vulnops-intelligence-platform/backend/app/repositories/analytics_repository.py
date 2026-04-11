from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, BusinessUnit, CveRecord, VulnerabilityFinding


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def summary_open_by_status(self) -> list[tuple[str, int]]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        stmt = (
            select(VulnerabilityFinding.status, func.count())
            .where(VulnerabilityFinding.status.in_(open_statuses))
            .group_by(VulnerabilityFinding.status)
        )
        rows = self.db.execute(stmt).all()
        return [(str(r[0]), int(r[1])) for r in rows]

    def summary_open_by_severity(self) -> list[tuple[str, int]]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        stmt = (
            select(CveRecord.severity, func.count())
            .join(
                VulnerabilityFinding,
                VulnerabilityFinding.cve_record_id == CveRecord.id,
            )
            .where(VulnerabilityFinding.status.in_(open_statuses))
            .group_by(CveRecord.severity)
        )
        rows = self.db.execute(stmt).all()
        return [(str(r[0]), int(r[1])) for r in rows]

    def total_open(self) -> int:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        q = select(func.count()).where(VulnerabilityFinding.status.in_(open_statuses))
        return int(self.db.scalar(q) or 0)

    def top_assets_by_open_findings(self, *, limit: int) -> list[dict]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        sub = (
            select(
                VulnerabilityFinding.asset_id.label("aid"),
                func.count().label("cnt"),
                func.max(CveRecord.cvss_base_score).label("max_cvss"),
            )
            .join(CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id)
            .where(VulnerabilityFinding.status.in_(open_statuses))
            .group_by(VulnerabilityFinding.asset_id)
            .subquery()
        )
        stmt = (
            select(Asset.id, Asset.name, sub.c.cnt, sub.c.max_cvss)
            .join(sub, Asset.id == sub.c.aid)
            .order_by(sub.c.cnt.desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "asset_id": str(r[0]),
                "asset_name": r[1],
                "open_findings": int(r[2]),
                "max_cvss": float(r[3]) if r[3] is not None else None,
            }
            for r in rows
        ]

    def business_unit_risk(self, *, limit: int) -> list[dict]:
        """Open findings aggregated per business unit."""
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        crit_case = case(
            (CveRecord.severity.in_(("CRITICAL", "HIGH")), 1),
            else_=0,
        )
        stmt = (
            select(
                BusinessUnit.id,
                BusinessUnit.code,
                BusinessUnit.name,
                func.count(VulnerabilityFinding.id).label("open_cnt"),
                func.sum(crit_case).label("crit_high"),
            )
            .join(Asset, Asset.business_unit_id == BusinessUnit.id)
            .join(VulnerabilityFinding, VulnerabilityFinding.asset_id == Asset.id)
            .join(CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id)
            .where(VulnerabilityFinding.status.in_(open_statuses))
            .group_by(BusinessUnit.id, BusinessUnit.code, BusinessUnit.name)
            .order_by(func.count(VulnerabilityFinding.id).desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "business_unit_id": str(r[0]),
                "business_unit_code": r[1],
                "business_unit_name": r[2],
                "open_findings": int(r[3]),
                "critical_or_high": int(r[4] or 0),
            }
            for r in rows
        ]
