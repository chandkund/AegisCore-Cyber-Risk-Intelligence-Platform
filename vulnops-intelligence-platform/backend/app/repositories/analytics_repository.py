from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, BusinessUnit, CveRecord, VulnerabilityFinding


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def summary_open_by_status(self, *, tenant_id: uuid.UUID) -> list[tuple[str, int]]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        stmt = (
            select(VulnerabilityFinding.status, func.count())
            .where(
                VulnerabilityFinding.status.in_(open_statuses),
                VulnerabilityFinding.tenant_id == tenant_id,
            )
            .group_by(VulnerabilityFinding.status)
        )
        rows = self.db.execute(stmt).all()
        return [(str(r[0]), int(r[1])) for r in rows]

    def summary_open_by_severity(self, *, tenant_id: uuid.UUID) -> list[tuple[str, int]]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        stmt = (
            select(CveRecord.severity, func.count())
            .join(
                VulnerabilityFinding,
                VulnerabilityFinding.cve_record_id == CveRecord.id,
            )
            .where(
                VulnerabilityFinding.status.in_(open_statuses),
                VulnerabilityFinding.tenant_id == tenant_id,
            )
            .group_by(CveRecord.severity)
        )
        rows = self.db.execute(stmt).all()
        return [(str(r[0]), int(r[1])) for r in rows]

    def total_open(self, *, tenant_id: uuid.UUID) -> int:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        q = select(func.count()).where(
            VulnerabilityFinding.status.in_(open_statuses),
            VulnerabilityFinding.tenant_id == tenant_id,
        )
        return int(self.db.scalar(q) or 0)

    def top_assets_by_open_findings(self, *, tenant_id: uuid.UUID, limit: int) -> list[dict]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        sub = (
            select(
                VulnerabilityFinding.asset_id.label("aid"),
                func.count().label("cnt"),
                func.max(CveRecord.cvss_base_score).label("max_cvss"),
            )
            .join(CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id)
            .where(
                VulnerabilityFinding.status.in_(open_statuses),
                VulnerabilityFinding.tenant_id == tenant_id,
            )
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

    def business_unit_risk(self, *, tenant_id: uuid.UUID, limit: int) -> list[dict]:
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
            .where(
                VulnerabilityFinding.status.in_(open_statuses),
                VulnerabilityFinding.tenant_id == tenant_id,
            )
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

    def risk_trend(self, *, tenant_id: uuid.UUID, days: int) -> list[dict]:
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")
        start_date = date.today() - timedelta(days=days - 1)
        stmt = (
            select(
                func.date(VulnerabilityFinding.discovered_at).label("bucket_date"),
                func.count(VulnerabilityFinding.id).label("opened_count"),
                func.avg(VulnerabilityFinding.risk_score).label("avg_risk_score"),
            )
            .where(
                VulnerabilityFinding.tenant_id == tenant_id,
                VulnerabilityFinding.status.in_(open_statuses),
                func.date(VulnerabilityFinding.discovered_at) >= start_date,
            )
            .group_by(func.date(VulnerabilityFinding.discovered_at))
            .order_by(func.date(VulnerabilityFinding.discovered_at).asc())
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "date": r.bucket_date.isoformat() if r.bucket_date else "",
                "opened_count": int(r.opened_count or 0),
                "avg_risk_score": round(float(r.avg_risk_score), 2) if r.avg_risk_score is not None else None,
            }
            for r in rows
        ]

    def sla_forecast(self, *, tenant_id: uuid.UUID) -> dict:
        now = datetime.now(timezone.utc)
        open_statuses = ("OPEN", "IN_PROGRESS", "RISK_ACCEPTED")

        due_stmt = select(
            func.count(case((VulnerabilityFinding.due_at < now, 1))).label("overdue_now"),
            func.count(
                case(
                    (
                        (VulnerabilityFinding.due_at >= now)
                        & (VulnerabilityFinding.due_at < now + timedelta(days=7)),
                        1,
                    )
                )
            ).label("due_next_7_days"),
            func.count(
                case(
                    (
                        (VulnerabilityFinding.due_at >= now)
                        & (VulnerabilityFinding.due_at < now + timedelta(days=14)),
                        1,
                    )
                )
            ).label("due_next_14_days"),
        ).where(
            VulnerabilityFinding.tenant_id == tenant_id,
            VulnerabilityFinding.status.in_(open_statuses),
            VulnerabilityFinding.due_at.is_not(None),
        )
        overdue_now, due_next_7_days, due_next_14_days = self.db.execute(due_stmt).one()

        resolved_last_14_stmt = select(func.count(VulnerabilityFinding.id)).where(
            VulnerabilityFinding.tenant_id == tenant_id,
            VulnerabilityFinding.remediated_at.is_not(None),
            VulnerabilityFinding.remediated_at >= now - timedelta(days=14),
        )
        resolved_last_14_days = int(self.db.scalar(resolved_last_14_stmt) or 0)
        daily_velocity = resolved_last_14_days / 14.0

        projected_resolved_7 = int(round(daily_velocity * 7))
        projected_resolved_14 = int(round(daily_velocity * 14))

        predicted_breaches_7 = max(0, int(due_next_7_days or 0) - projected_resolved_7)
        predicted_breaches_14 = max(0, int(due_next_14_days or 0) - projected_resolved_14)
        if predicted_breaches_14 < predicted_breaches_7:
            predicted_breaches_14 = predicted_breaches_7

        return {
            "overdue_now": int(overdue_now or 0),
            "due_next_7_days": int(due_next_7_days or 0),
            "due_next_14_days": int(due_next_14_days or 0),
            "resolved_last_14_days": resolved_last_14_days,
            "projected_daily_resolve_rate": round(daily_velocity, 2),
            "predicted_breaches_next_7_days": predicted_breaches_7,
            "predicted_breaches_next_14_days": predicted_breaches_14,
        }
