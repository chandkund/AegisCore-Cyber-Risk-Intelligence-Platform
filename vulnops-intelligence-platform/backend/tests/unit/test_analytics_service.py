from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.oltp import Asset, BusinessUnit, CveRecord, Organization, VulnerabilityFinding
from app.services.analytics_service import AnalyticsService


def _seed_analytics_data(db: Session, tenant_id: uuid.UUID, bu_code: str = "ENG") -> None:
    bu = BusinessUnit(id=uuid.uuid4(), code=bu_code, name=f"Engineering-{bu_code}")
    db.add(bu)
    db.flush()
    asset = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="prod-api-01",
        asset_type="server",
        business_unit_id=bu.id,
        criticality=1,
        is_external=True,
    )
    cve_1 = CveRecord(
        id=uuid.uuid4(),
        cve_id=f"CVE-2026-{bu_code}-001",
        severity="CRITICAL",
        cvss_base_score=Decimal("9.8"),
        exploit_available=True,
    )
    cve_2 = CveRecord(
        id=uuid.uuid4(),
        cve_id=f"CVE-2026-{bu_code}-002",
        severity="HIGH",
        cvss_base_score=Decimal("8.0"),
        exploit_available=False,
    )
    cve_3 = CveRecord(
        id=uuid.uuid4(),
        cve_id=f"CVE-2026-{bu_code}-003",
        severity="MEDIUM",
        cvss_base_score=Decimal("6.5"),
        exploit_available=False,
    )
    now = datetime.now(timezone.utc)
    findings = [
        VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            asset_id=asset.id,
            cve_record_id=cve_1.id,
            status="OPEN",
            discovered_at=now - timedelta(days=2),
            due_at=now - timedelta(days=1),  # overdue
            risk_score=Decimal("88.5"),
        ),
        VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            asset_id=asset.id,
            cve_record_id=cve_2.id,
            status="IN_PROGRESS",
            discovered_at=now - timedelta(days=1),
            due_at=now + timedelta(days=3),
            risk_score=Decimal("79.0"),
        ),
        VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            asset_id=asset.id,
            cve_record_id=cve_3.id,
            status="REMEDIATED",
            discovered_at=now - timedelta(days=10),
            remediated_at=now - timedelta(days=2),
            risk_score=Decimal("65.0"),
        ),
    ]
    db.add_all([asset, cve_1, cve_2, cve_3, *findings])
    db.flush()


def test_risk_trend_and_sla_forecast(db: Session):
    tenant_id = uuid.UUID("00000000-0000-4000-8000-0000000000AA")
    db.add(Organization(id=tenant_id, name="Trend Org", code="trend-org"))
    _seed_analytics_data(db, tenant_id)

    service = AnalyticsService(db)
    trend = service.risk_trend(tenant_id=tenant_id, days=30)
    forecast = service.sla_forecast(tenant_id=tenant_id)

    assert trend.days == 30
    assert len(trend.points) >= 1
    assert any(p.opened_count >= 1 for p in trend.points)
    assert forecast.overdue_now >= 1
    assert forecast.due_next_7_days >= 1
    assert forecast.predicted_breaches_next_14_days >= forecast.predicted_breaches_next_7_days


def test_analytics_tenant_isolation(db: Session):
    tenant_a = uuid.UUID("00000000-0000-4000-8000-0000000000AB")
    tenant_b = uuid.UUID("00000000-0000-4000-8000-0000000000AC")
    db.add_all(
        [
            Organization(id=tenant_a, name="Org A", code="orga"),
            Organization(id=tenant_b, name="Org B", code="orgb"),
        ]
    )
    _seed_analytics_data(db, tenant_a, bu_code="ENGA")
    _seed_analytics_data(db, tenant_b, bu_code="ENGB")

    service = AnalyticsService(db)
    summary_a = service.summary(tenant_id=tenant_a)
    summary_b = service.summary(tenant_id=tenant_b)

    assert summary_a.total_open_findings == 2
    assert summary_b.total_open_findings == 2
