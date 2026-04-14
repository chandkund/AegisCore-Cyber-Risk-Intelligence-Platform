from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.oltp import (
    Asset,
    AssetDependency,
    BusinessUnit,
    CveRecord,
    Organization,
    VulnerabilityFinding,
)
from app.services.attack_path_service import AttackPathService


def test_blast_radius_from_asset(db: Session):
    tenant_id = uuid.UUID("00000000-0000-4000-8000-0000000000BA")
    db.add(Organization(id=tenant_id, name="Attack Org", code="attack-org"))
    bu = BusinessUnit(id=uuid.uuid4(), code="SECATTACK", name="Security")
    db.add(bu)
    db.flush()

    a1 = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="edge-gateway",
        asset_type="network",
        business_unit_id=bu.id,
        criticality=1,
        is_external=True,
    )
    a2 = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="app-server",
        asset_type="server",
        business_unit_id=bu.id,
        criticality=2,
        is_external=False,
    )
    a3 = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="db-server",
        asset_type="database",
        business_unit_id=bu.id,
        criticality=1,
        is_external=False,
    )
    db.add_all([a1, a2, a3])

    db.add_all(
        [
            AssetDependency(
                tenant_id=tenant_id,
                source_asset_id=a1.id,
                target_asset_id=a2.id,
                dependency_type="network",
                trust_level="high",
                lateral_movement_score=Decimal("0.80"),
            ),
            AssetDependency(
                tenant_id=tenant_id,
                source_asset_id=a2.id,
                target_asset_id=a3.id,
                dependency_type="application",
                trust_level="medium",
                lateral_movement_score=Decimal("0.70"),
            ),
        ]
    )

    cve = CveRecord(
        id=uuid.uuid4(),
        cve_id="CVE-2026-9001",
        severity="CRITICAL",
        cvss_base_score=Decimal("9.4"),
        exploit_available=True,
    )
    db.add(cve)
    db.add(
        VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            asset_id=a2.id,
            cve_record_id=cve.id,
            status="OPEN",
            discovered_at=datetime.now(timezone.utc),
            risk_score=Decimal("88.0"),
        )
    )
    db.flush()

    result = AttackPathService(db, tenant_id=tenant_id).from_asset(str(a1.id), max_depth=3)
    assert result is not None
    assert result.total_impacted_assets == 3
    assert result.internet_exposed_assets == 1
    assert result.high_risk_findings_in_radius >= 1
    assert len(result.edges) == 2


def test_blast_radius_is_tenant_scoped(db: Session):
    tenant_a = uuid.UUID("00000000-0000-4000-8000-0000000000BB")
    tenant_b = uuid.UUID("00000000-0000-4000-8000-0000000000BC")
    bua = BusinessUnit(id=uuid.uuid4(), code="SECATTA", name="Security A")
    bub = BusinessUnit(id=uuid.uuid4(), code="SECATTB", name="Security B")
    db.add_all(
        [
            Organization(id=tenant_a, name="Tenant A", code="tena"),
            Organization(id=tenant_b, name="Tenant B", code="tenb"),
            bua,
            bub,
        ]
    )
    db.flush()

    a_asset = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_a,
        name="tenant-a-asset",
        asset_type="server",
        business_unit_id=bua.id,
        criticality=2,
        is_external=False,
    )
    b_asset = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_b,
        name="tenant-b-asset",
        asset_type="server",
        business_unit_id=bub.id,
        criticality=2,
        is_external=False,
    )
    db.add_all([a_asset, b_asset])
    db.flush()

    result = AttackPathService(db, tenant_id=tenant_a).from_asset(str(b_asset.id), max_depth=2)
    assert result is None
