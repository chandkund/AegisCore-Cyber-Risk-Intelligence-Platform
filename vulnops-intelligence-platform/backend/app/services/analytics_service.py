from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.oltp import PolicyRule, VulnerabilityFinding
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import (
    AnalyticsSummary,
    BusinessUnitRiskRow,
    RiskTrendPoint,
    RiskTrendResponse,
    SeverityCount,
    SlaForecastResponse,
    StatusCount,
    TopAssetRow,
)
from app.schemas.compliance import ComplianceReportOut, RootCauseCluster


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AnalyticsRepository(db)

    def summary(self, *, tenant_id: uuid.UUID) -> AnalyticsSummary:
        total = self.repo.total_open(tenant_id=tenant_id)
        by_status = [
            StatusCount(status=s, count=c)
            for s, c in self.repo.summary_open_by_status(tenant_id=tenant_id)
        ]
        by_sev = [
            SeverityCount(severity=s, count=c)
            for s, c in self.repo.summary_open_by_severity(tenant_id=tenant_id)
        ]
        return AnalyticsSummary(
            total_open_findings=total,
            by_status=by_status,
            by_severity=by_sev,
        )

    def top_assets(self, *, tenant_id: uuid.UUID, limit: int = 20) -> list[TopAssetRow]:
        rows = self.repo.top_assets_by_open_findings(tenant_id=tenant_id, limit=limit)
        return [TopAssetRow(**r) for r in rows]

    def business_units(
        self, *, tenant_id: uuid.UUID, limit: int = 50
    ) -> list[BusinessUnitRiskRow]:
        rows = self.repo.business_unit_risk(tenant_id=tenant_id, limit=limit)
        return [BusinessUnitRiskRow(**r) for r in rows]

    def risk_trend(self, *, tenant_id: uuid.UUID, days: int = 30) -> RiskTrendResponse:
        rows = self.repo.risk_trend(tenant_id=tenant_id, days=days)
        return RiskTrendResponse(
            days=days,
            points=[RiskTrendPoint(**r) for r in rows],
        )

    def sla_forecast(self, *, tenant_id: uuid.UUID) -> SlaForecastResponse:
        return SlaForecastResponse(**self.repo.sla_forecast(tenant_id=tenant_id))

    def root_cause_clusters(
        self, *, tenant_id: uuid.UUID, limit: int = 10
    ) -> list[RootCauseCluster]:
        rows = self.db.execute(
            select(VulnerabilityFinding)
            .where(
                VulnerabilityFinding.tenant_id == tenant_id,
                VulnerabilityFinding.status.in_(["OPEN", "IN_PROGRESS", "RISK_ACCEPTED"]),
            )
            .limit(1000)
        ).scalars().all()
        buckets: dict[str, list[VulnerabilityFinding]] = {}
        for f in rows:
            notes = (f.notes or "").lower()
            if "patch" in notes:
                key = "patching_gap"
            elif "config" in notes or "misconfig" in notes:
                key = "misconfiguration"
            elif "credential" in notes or "password" in notes:
                key = "credential_hygiene"
            else:
                key = "unclassified"
            buckets.setdefault(key, []).append(f)
        out: list[RootCauseCluster] = []
        for k, items in sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True)[:limit]:
            out.append(
                RootCauseCluster(
                    cluster_key=k,
                    finding_count=len(items),
                    top_assets=[str(i.asset_id) for i in items[:3]],
                    representative_cves=[str(i.cve_record_id) for i in items[:3]],
                )
            )
        return out

    def compliance_report(self, *, tenant_id: uuid.UUID) -> ComplianceReportOut:
        now = datetime.now(timezone.utc)
        open_statuses = ["OPEN", "IN_PROGRESS", "RISK_ACCEPTED"]
        total_open = int(
            self.db.scalar(
                select(func.count()).select_from(VulnerabilityFinding).where(
                    VulnerabilityFinding.tenant_id == tenant_id,
                    VulnerabilityFinding.status.in_(open_statuses),
                )
            )
            or 0
        )
        overdue_count = int(
            self.db.scalar(
                select(func.count()).select_from(VulnerabilityFinding).where(
                    VulnerabilityFinding.tenant_id == tenant_id,
                    VulnerabilityFinding.status.in_(open_statuses),
                    VulnerabilityFinding.due_at.is_not(None),
                    VulnerabilityFinding.due_at < now,
                )
            )
            or 0
        )
        avg_remediation_days = float(
            self.db.scalar(
                select(
                    func.coalesce(
                        func.avg(
                            func.extract(
                                "epoch",
                                VulnerabilityFinding.remediated_at - VulnerabilityFinding.discovered_at,
                            )
                            / 86400.0
                        ),
                        0.0,
                    )
                ).where(
                    VulnerabilityFinding.tenant_id == tenant_id,
                    VulnerabilityFinding.remediated_at.is_not(None),
                )
            )
            or 0.0
        )
        policy_violations_count = len(
            self.db.execute(
                select(PolicyRule).where(
                    PolicyRule.tenant_id == tenant_id, PolicyRule.is_enabled.is_(True)
                )
            ).scalars().all()
        ) * max(1, min(total_open, 10))
        return ComplianceReportOut(
            generated_at=now,
            total_open=total_open,
            overdue_count=overdue_count,
            avg_remediation_days=round(avg_remediation_days, 2),
            sla_breach_rate=round((overdue_count / total_open) if total_open else 0.0, 3),
            policy_violations_count=policy_violations_count,
        )
