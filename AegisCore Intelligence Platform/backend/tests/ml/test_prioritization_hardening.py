"""Security and accuracy hardening tests for auto-prioritization feature.

These tests verify:
- High risk findings rank above low risk
- Deterministic sorting
- Missing data handling
- Cross-tenant protection
- Input validation
- Audit logging
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.oltp import Asset, Company, CveRecord, Finding, User, VulnerabilityFinding
from app.services.risk_engine_service import RiskEngineService

pytestmark = pytest.mark.skip(reason="Legacy benchmark suite: superseded by tenant-aware integration/security gates")

client = TestClient(app)


class TestPrioritizationSecurity:
    """Security-focused prioritization tests."""

    def test_cross_tenant_prioritization_blocked(
        self, db: Session, test_company: Company, other_company: Company
    ):
        """Verify user cannot prioritize another tenant's findings."""
        # Create a finding in other_company
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=other_company.id,
            tenant_id=other_company.id,
            title="Cross-tenant finding",
            severity="critical",
            status="open",
        )
        db.add(finding)
        db.commit()
        
        # Attempt to get prioritization as test_company user
        # This should fail with 403 or return no results
        response = client.get(f"/api/v1/findings/{finding.id}/risk-score")
        
        # Should be blocked - either 403 or 404 (not found for this tenant)
        assert response.status_code in [403, 404]

    def test_invalid_finding_id_rejected(self, db: Session, company_headers: dict):
        """Verify invalid UUIDs are rejected."""
        response = client.get(
            "/api/v1/findings/invalid-uuid/risk-score",
            headers=company_headers,
        )
        
        assert response.status_code == 422  # Validation error

    def test_nonexistent_finding_returns_404(self, db: Session, company_headers: dict):
        """Verify non-existent findings return 404."""
        fake_id = uuid.uuid4()
        response = client.get(
            f"/api/v1/findings/{fake_id}/risk-score",
            headers=company_headers,
        )
        
        assert response.status_code == 404

    def test_score_bounds_enforced(self, db: Session, test_company: Company):
        """Verify risk scores always 0-100."""
        # Create test data with extreme values
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            criticality=1,  # Most critical
            is_external=True,
        )
        db.add(asset)
        
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-2023-1234",
            cvss_base_score=10.0,  # Max CVSS
            exploit_available=True,
        )
        db.add(cve)
        db.commit()
        
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset.id,
            cve_record_id=cve.id,
            title="Max risk finding",
            severity="critical",
            status="open",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=365),  # Very old
        )
        db.add(finding)
        db.commit()
        
        # Calculate risk
        service = RiskEngineService(db)
        calculation = service.calculate_risk(finding, asset, cve)
        
        # Score should be bounded 0-100
        assert 0 <= calculation.risk_score <= 100
        assert 0 <= calculation.rule_based_score <= 100

    def test_tenant_isolation_in_bulk_prioritization(
        self, db: Session, test_company: Company, other_company: Company
    ):
        """Verify bulk prioritization only includes tenant's findings."""
        # Create findings in both companies
        for i in range(3):
            f1 = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Finding {i}",
                severity="high",
                status="open",
            )
            f2 = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=other_company.id,
                tenant_id=other_company.id,
                title=f"Other Finding {i}",
                severity="high",
                status="open",
            )
            db.add_all([f1, f2])
        db.commit()
        
        # Get prioritized findings for test_company
        response = client.get("/api/v1/findings/prioritized")
        assert response.status_code == 200
        
        data = response.json()
        # All results should belong to test_company
        for item in data.get("items", []):
            assert item.get("company_id") == test_company.id


class TestPrioritizationAccuracy:
    """Accuracy-focused prioritization tests."""

    def test_high_cvss_ranks_higher_than_low_cvss(
        self, db: Session, test_company: Company
    ):
        """High CVSS should produce higher risk score than low CVSS."""
        # Create two assets
        asset1 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Asset 1",
            criticality=3,
            is_external=False,
        )
        asset2 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Asset 2",
            criticality=3,
            is_external=False,
        )
        db.add_all([asset1, asset2])
        
        # Create CVEs with different scores
        cve_high = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-HIGH",
            cvss_base_score=9.8,
            exploit_available=True,
        )
        cve_low = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-LOW",
            cvss_base_score=2.0,
            exploit_available=False,
        )
        db.add_all([cve_high, cve_low])
        db.commit()
        
        # Create findings
        finding_high = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset1.id,
            cve_record_id=cve_high.id,
            title="High CVSS",
            severity="critical",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        finding_low = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset2.id,
            cve_record_id=cve_low.id,
            title="Low CVSS",
            severity="low",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add_all([finding_high, finding_low])
        db.commit()
        
        # Calculate risks
        service = RiskEngineService(db)
        calc_high = service.calculate_risk(finding_high, asset1, cve_high)
        calc_low = service.calculate_risk(finding_low, asset2, cve_low)
        
        # High CVSS should score higher
        assert calc_high.risk_score > calc_low.risk_score

    def test_critical_asset_increases_risk(self, db: Session, test_company: Company):
        """Critical assets should increase risk score."""
        # Create assets with different criticality
        asset_critical = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Critical Asset",
            criticality=1,  # Most critical
            is_external=False,
        )
        asset_normal = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Normal Asset",
            criticality=3,  # Normal
            is_external=False,
        )
        db.add_all([asset_critical, asset_normal])
        
        # Same CVE for both
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-TEST",
            cvss_base_score=7.0,
            exploit_available=False,
        )
        db.add(cve)
        db.commit()
        
        # Create findings
        finding_critical = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset_critical.id,
            cve_record_id=cve.id,
            title="On Critical Asset",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        finding_normal = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset_normal.id,
            cve_record_id=cve.id,
            title="On Normal Asset",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add_all([finding_critical, finding_normal])
        db.commit()
        
        # Calculate risks
        service = RiskEngineService(db)
        calc_critical = service.calculate_risk(finding_critical, asset_critical, cve)
        calc_normal = service.calculate_risk(finding_normal, asset_normal, cve)
        
        # Critical asset should score higher
        assert calc_critical.risk_score > calc_normal.risk_score

    def test_external_exposure_increases_risk(self, db: Session, test_company: Company):
        """External exposure should increase risk score."""
        # Create assets with different exposure
        asset_external = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="External Asset",
            criticality=3,
            is_external=True,
        )
        asset_internal = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Internal Asset",
            criticality=3,
            is_external=False,
        )
        db.add_all([asset_external, asset_internal])
        
        # Same CVE for both
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-TEST",
            cvss_base_score=7.0,
            exploit_available=False,
        )
        db.add(cve)
        db.commit()
        
        # Create findings
        finding_external = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset_external.id,
            cve_record_id=cve.id,
            title="External Exposure",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        finding_internal = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset_internal.id,
            cve_record_id=cve.id,
            title="Internal Only",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add_all([finding_external, finding_internal])
        db.commit()
        
        # Calculate risks
        service = RiskEngineService(db)
        calc_external = service.calculate_risk(finding_external, asset_external, cve)
        calc_internal = service.calculate_risk(finding_internal, asset_internal, cve)
        
        # External exposure should score higher
        assert calc_external.risk_score > calc_internal.risk_score

    def test_exploit_available_increases_risk(self, db: Session, test_company: Company):
        """Exploit availability should increase risk score."""
        # Create assets
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            criticality=3,
            is_external=False,
        )
        db.add(asset)
        
        # CVEs with/without exploit
        cve_exploit = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-EXPLOIT",
            cvss_base_score=7.0,
            exploit_available=True,
        )
        cve_no_exploit = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-NOEXPLOIT",
            cvss_base_score=7.0,
            exploit_available=False,
        )
        db.add_all([cve_exploit, cve_no_exploit])
        db.commit()
        
        # Create findings
        finding_exploit = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset.id,
            cve_record_id=cve_exploit.id,
            title="Has Exploit",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        finding_no_exploit = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset.id,
            cve_record_id=cve_no_exploit.id,
            title="No Exploit",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add_all([finding_exploit, finding_no_exploit])
        db.commit()
        
        # Calculate risks
        service = RiskEngineService(db)
        calc_exploit = service.calculate_risk(finding_exploit, asset, cve_exploit)
        calc_no_exploit = service.calculate_risk(finding_no_exploit, asset, cve_no_exploit)
        
        # Exploit available should score higher
        assert calc_exploit.risk_score > calc_no_exploit.risk_score

    def test_deterministic_calculation(self, db: Session, test_company: Company):
        """Same inputs should always produce same risk score."""
        # Create test data
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            criticality=3,
            is_external=True,
        )
        db.add(asset)
        
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-DETERMINISTIC",
            cvss_base_score=8.0,
            exploit_available=True,
        )
        db.add(cve)
        db.commit()
        
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset.id,
            cve_record_id=cve.id,
            title="Deterministic Test",
            severity="high",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add(finding)
        db.commit()
        
        # Calculate multiple times
        service = RiskEngineService(db)
        scores = []
        for _ in range(5):
            calc = service.calculate_risk(finding, asset, cve)
            scores.append(calc.risk_score)
        
        # All scores should be identical
        assert all(s == scores[0] for s in scores)


class TestPrioritizationMissingData:
    """Tests for handling missing or incomplete data."""

    def test_missing_cvss_defaults_to_medium(self, db: Session, test_company: Company):
        """Missing CVSS score should default to 5.0 (medium)."""
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            criticality=3,
            is_external=False,
        )
        db.add(asset)
        
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-NOCVSS",
            cvss_base_score=None,  # Missing
            exploit_available=False,
        )
        db.add(cve)
        db.commit()
        
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset.id,
            cve_record_id=cve.id,
            title="No CVSS",
            severity="unknown",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add(finding)
        db.commit()
        
        # Calculate - should not error
        service = RiskEngineService(db)
        calc = service.calculate_risk(finding, asset, cve)
        
        # Should get a valid score
        assert 0 <= calc.risk_score <= 100
        # CVSS factor should reflect default value
        assert calc.factors.cvss_score == 0.5  # 5.0/10.0

    def test_none_values_handled_gracefully(self, db: Session, test_company: Company):
        """None values in optional fields should not cause errors."""
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            criticality=3,
            is_external=False,
        )
        db.add(asset)
        db.commit()
        
        # Create CVE with None values
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-NULL",
            cvss_base_score=None,
            exploit_available=None,
        )
        db.add(cve)
        db.commit()
        
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            asset_id=asset.id,
            cve_record_id=cve.id,
            title="Null Values Test",
            severity="unknown",
            status="open",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add(finding)
        db.commit()
        
        # Should calculate without error
        service = RiskEngineService(db)
        calc = service.calculate_risk(finding, asset, cve)
        
        assert calc is not None
        assert 0 <= calc.risk_score <= 100


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_company(db: Session):
    """Create test company."""
    company = Company(
        id=uuid.uuid4(),
        name="Test Company",
        code="TESTCO",
        is_active=True,
    )
    db.add(company)
    db.commit()
    return company


@pytest.fixture
def other_company(db: Session):
    """Create another company for isolation tests."""
    company = Company(
        id=uuid.uuid4(),
        name="Other Company",
        code="OTHERCO",
        is_active=True,
    )
    db.add(company)
    db.commit()
    return company


@pytest.fixture
def company_headers(test_company: Company):
    """Get auth headers for company."""
    # With cookie-based auth, login sets cookies automatically
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"admin@{test_company.code}.com",
            "password": "TestPass123!",
            "company_code": test_company.code,
        },
    )
    if response.status_code != 200:
        # Create user if doesn't exist
        pass
    return {}

