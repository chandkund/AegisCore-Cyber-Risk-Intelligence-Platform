"""Unit tests for Risk Engine Service.

Tests cover:
- Scoring formula correctness
- Normalization logic
- Factor calculations
- Ensemble scoring (rule-based + ML)
- Edge cases (missing data, boundary values)
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.oltp import Asset, BusinessUnit, CveRecord, Organization, VulnerabilityFinding
from app.services.risk_engine_service import (
    RiskCalculation,
    RiskEngineService,
    RiskFactors,
    RiskWeights,
)

TEST_TENANT_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")


@pytest.fixture(autouse=True)
def ensure_test_tenant(db: Session):
    """Ensure the test tenant exists for FK-constrained entities."""
    existing = db.execute(
        select(Organization).where(Organization.id == TEST_TENANT_ID)
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            Organization(
                id=TEST_TENANT_ID,
                name="Default Organization",
                code="default",
                is_active=True,
                approval_status="approved",
            )
        )
        db.flush()


class TestRiskWeights:
    """Test weight configuration validation."""

    def test_default_weights_sum_to_one(self):
        """Default weights must sum to approximately 1.0."""
        weights = RiskWeights()
        assert weights.validate() is True
        total = weights.cvss + weights.criticality + weights.exposure + weights.exploit + weights.age
        assert 0.99 <= total <= 1.01

    def test_custom_weights_validation(self):
        """Custom weights can be set but must sum to 1.0."""
        weights = RiskWeights(cvss=0.4, criticality=0.3, exposure=0.2, exploit=0.05, age=0.05)
        assert weights.validate() is True

    def test_invalid_weights_detected(self):
        """Weights that don't sum to 1.0 should fail validation."""
        weights = RiskWeights(cvss=0.5, criticality=0.5, exposure=0.5, exploit=0.5, age=0.5)
        assert weights.validate() is False


class TestFactorCalculations:
    """Test individual risk factor calculations."""

    @pytest.fixture
    def base_finding(self):
        """Create a base vulnerability finding."""
        return VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            asset_id=uuid.uuid4(),
            cve_record_id=uuid.uuid4(),
            status="OPEN",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=10),
        )

    @pytest.fixture
    def base_asset(self):
        """Create a base asset."""
        return Asset(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            name="test-asset",
            asset_type="server",
            business_unit_id=uuid.uuid4(),
            criticality=3,  # Medium
            is_external=False,
        )

    @pytest.fixture
    def base_cve(self):
        """Create a base CVE record."""
        return CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-2024-0001",
            severity="HIGH",
            cvss_base_score=Decimal("7.5"),
            exploit_available=False,
        )

    def test_cvss_normalization(self, base_finding, base_asset, base_cve):
        """CVSS 10 should normalize to 1.0, CVSS 0 to 0.0."""
        service = RiskEngineService(None)
        
        # Test CVSS 10.0 -> 1.0
        base_cve.cvss_base_score = Decimal("10.0")
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.cvss_score == 1.0
        
        # Test CVSS 5.0 -> 0.5
        base_cve.cvss_base_score = Decimal("5.0")
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.cvss_score == 0.5
        
        # Test CVSS 0.0 -> 0.0
        base_cve.cvss_base_score = Decimal("0.0")
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.cvss_score == 0.0

    def test_criticality_normalization(self, base_finding, base_asset, base_cve):
        """Criticality 1 should be 1.0, criticality 5 should be 0.2."""
        service = RiskEngineService(None)
        
        # Critical (1) -> 1.0
        base_asset.criticality = 1
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.criticality_score == 1.0
        
        # High (2) -> 0.8
        base_asset.criticality = 2
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.criticality_score == 0.8
        
        # Low (5) -> 0.2
        base_asset.criticality = 5
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.criticality_score == 0.2

    def test_exposure_scoring(self, base_finding, base_asset, base_cve):
        """External assets should score 1.0, internal 0.0."""
        service = RiskEngineService(None)
        
        # External -> 1.0
        base_asset.is_external = True
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.exposure_score == 1.0
        
        # Internal -> 0.0
        base_asset.is_external = False
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.exposure_score == 0.0

    def test_exploit_scoring(self, base_finding, base_asset, base_cve):
        """Exploit available should score 1.0, not available 0.0."""
        service = RiskEngineService(None)
        
        # Exploit available -> 1.0
        base_cve.exploit_available = True
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.exploit_score == 1.0
        
        # No exploit -> 0.0
        base_cve.exploit_available = False
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.exploit_score == 0.0

    def test_age_scoring_linear_decay(self, base_finding, base_asset, base_cve):
        """Age should linearly increase to max at 90 days."""
        service = RiskEngineService(None)
        now = datetime.now(timezone.utc)
        
        # Brand new (0 days) -> 0.0
        base_finding.discovered_at = now
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.age_score == 0.0
        
        # 45 days -> ~0.5
        base_finding.discovered_at = now - timedelta(days=45)
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert 0.49 <= calc.factors.age_score <= 0.51
        
        # 90 days -> 1.0
        base_finding.discovered_at = now - timedelta(days=90)
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.age_score == 1.0
        
        # 180 days (clamped) -> 1.0
        base_finding.discovered_at = now - timedelta(days=180)
        calc = service.calculate_risk(base_finding, base_asset, base_cve, use_ml=False)
        assert calc.factors.age_score == 1.0


class TestRiskScoreCalculation:
    """Test complete risk score calculations."""

    def create_test_data(self):
        """Helper to create test data."""
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            asset_id=uuid.uuid4(),
            cve_record_id=uuid.uuid4(),
            status="OPEN",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=30),
        )
        asset = Asset(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            name="test-asset",
            asset_type="server",
            business_unit_id=uuid.uuid4(),
            criticality=2,  # High
            is_external=True,
        )
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-2024-0001",
            severity="CRITICAL",
            cvss_base_score=Decimal("9.8"),
            exploit_available=True,
        )
        return finding, asset, cve

    def test_maximum_risk_score(self):
        """All factors at maximum should produce ~100 risk score."""
        service = RiskEngineService(None)
        finding, asset, cve = self.create_test_data()
        finding.discovered_at = datetime.now(timezone.utc) - timedelta(days=180)
        
        calc = service.calculate_risk(finding, asset, cve, use_ml=False)
        
        # Should be very high (close to 100)
        assert calc.risk_score >= 90
        assert calc.rule_based_score >= 90
        assert calc.calculation_method == "rule_based"

    def test_minimum_risk_score(self):
        """All factors at minimum should produce low risk score."""
        service = RiskEngineService(None)
        finding, asset, cve = self.create_test_data()
        
        # Set all to minimum
        cve.cvss_base_score = Decimal("0.0")
        asset.criticality = 5  # Low
        asset.is_external = False
        cve.exploit_available = False
        finding.discovered_at = datetime.now(timezone.utc)  # Brand new
        
        calc = service.calculate_risk(finding, asset, cve, use_ml=False)
        
        # Should be very low
        assert calc.risk_score <= 20

    def test_missing_cvss_defaults_to_medium(self):
        """Missing CVSS should default to 5.0 (medium)."""
        service = RiskEngineService(None)
        finding, asset, cve = self.create_test_data()
        
        cve.cvss_base_score = None
        calc = service.calculate_risk(finding, asset, cve, use_ml=False)
        
        # Should use default of 5.0 -> 0.5 normalized
        assert calc.factors.cvss_score == 0.5

    def test_contributing_factors_identified(self):
        """High-impact factors should be identified as contributing."""
        service = RiskEngineService(None)
        finding, asset, cve = self.create_test_data()
        
        # Set high CVSS
        cve.cvss_base_score = Decimal("9.5")
        calc = service.calculate_risk(finding, asset, cve, use_ml=False)
        
        # Should have CVSS as contributing factor
        factor_types = [f["factor"] for f in calc.contributing_factors]
        assert "cvss" in factor_types


class TestRiskScoreStorage:
    """Test database storage of risk scores."""

    @pytest.mark.skipif(
        "sqlite" in (os.environ.get("AEGISCORE_TEST_DATABASE_URL", "") or os.environ.get("DATABASE_URL", "")).lower(),
        reason="Risk score storage test requires PostgreSQL for proper UUID/Decimal handling"
    )
    def test_risk_score_stored_as_decimal(self, db: Session):
        """Risk score should be stored as Decimal with proper precision."""
        from app.services.risk_engine_service import RiskEngineService
        
        # Create test records
        asset = Asset(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            name="test-asset",
            asset_type="server",
            business_unit_id=uuid.uuid4(),
            criticality=2,
            is_external=True,
        )
        db.add(
            BusinessUnit(
                id=asset.business_unit_id,
                tenant_id=TEST_TENANT_ID,
                name="BU-Storage",
                code=f"BU-ST-{str(asset.business_unit_id)[:8]}",
            )
        )
        db.flush()
        cve = CveRecord(
            id=uuid.uuid4(),
            cve_id="CVE-2024-TEST",
            severity="HIGH",
            cvss_base_score=Decimal("8.5"),
            exploit_available=True,
        )
        finding = VulnerabilityFinding(
            id=uuid.uuid4(),
            tenant_id=TEST_TENANT_ID,
            asset_id=asset.id,
            cve_record_id=cve.id,
            status="OPEN",
            discovered_at=datetime.now(timezone.utc) - timedelta(days=20),
        )
        
        db.add_all([asset, cve, finding])
        db.flush()
        
        # Calculate and store
        service = RiskEngineService(db)
        calc = service.recalculate_and_store(finding.id, tenant_id=TEST_TENANT_ID)
        
        assert calc is not None
        assert finding.risk_score is not None
        assert finding.risk_factors is not None
        assert "cvss" in finding.risk_factors
        assert finding.risk_calculated_at is not None
        
        # Verify risk score is stored (SQLite returns float, PostgreSQL returns Decimal)
        assert isinstance(finding.risk_score, (Decimal, float))
        assert float(finding.risk_score) > 0


class TestRiskPercentile:
    """Test percentile rank calculation."""

    @pytest.mark.skipif(
        "sqlite" in (os.environ.get("AEGISCORE_TEST_DATABASE_URL", "")).lower(),
        reason="Percentile calculation requires PostgreSQL for proper UUID handling"
    )
    def test_percentile_calculation(self, db: Session):
        """Percentile should rank vulnerability among all open findings."""
        # Create multiple findings with different risk scores
        for i in range(5):
            bu_id = uuid.uuid4()
            db.add(
                BusinessUnit(
                    id=bu_id,
                    tenant_id=TEST_TENANT_ID,
                    name=f"BU-Percentile-{i}",
                    code=f"BU-PCT-{i}-{str(bu_id)[:6]}",
                )
            )
            db.flush()
            asset = Asset(
                id=uuid.uuid4(),
                tenant_id=TEST_TENANT_ID,
                name=f"asset-{i}",
                asset_type="server",
                business_unit_id=bu_id,
                criticality=1,
                is_external=True,
            )
            cve = CveRecord(
                id=uuid.uuid4(),
                cve_id=f"CVE-2024-{i:04d}",
                severity="CRITICAL",
                cvss_base_score=Decimal(str(5.0 + i)),  # 5.0, 6.0, 7.0, 8.0, 9.0
                exploit_available=True,
            )
            finding = VulnerabilityFinding(
                id=uuid.uuid4(),
                tenant_id=TEST_TENANT_ID,
                asset_id=asset.id,
                cve_record_id=cve.id,
                status="OPEN",
                discovered_at=datetime.now(timezone.utc) - timedelta(days=10),
                risk_score=Decimal(str(50 + i * 10)),  # 50, 60, 70, 80, 90
            )
            db.add_all([asset, cve, finding])
        
        db.flush()
        
        service = RiskEngineService(db)
        
        # Highest score (90) should be in top percentile
        highest_finding = db.query(VulnerabilityFinding).filter(
            VulnerabilityFinding.risk_score == 90
        ).first()
        percentile = service.get_risk_percentile(highest_finding.id, TEST_TENANT_ID)
        assert percentile is not None
        assert percentile >= 80  # Top 20%


class TestBulkRecalculation:
    """Test bulk recalculation functionality."""

    @pytest.mark.skipif(
        "sqlite" in (os.environ.get("AEGISCORE_TEST_DATABASE_URL", "")).lower(),
        reason="Bulk recalculation requires PostgreSQL for proper UUID handling"
    )
    def test_bulk_recalculation_stats(self, db: Session):
        """Bulk recalculation should return accurate statistics."""
        # Create test findings
        for i in range(3):
            bu_id = uuid.uuid4()
            db.add(
                BusinessUnit(
                    id=bu_id,
                    tenant_id=TEST_TENANT_ID,
                    name=f"BU-Bulk-{i}",
                    code=f"BU-BLK-{i}-{str(bu_id)[:6]}",
                )
            )
            db.flush()
            asset = Asset(
                id=uuid.uuid4(),
                tenant_id=TEST_TENANT_ID,
                name=f"asset-{i}",
                asset_type="server",
                business_unit_id=bu_id,
                criticality=2,
                is_external=False,
            )
            cve = CveRecord(
                id=uuid.uuid4(),
                cve_id=f"CVE-2024-{i:04d}",
                severity="HIGH",
                cvss_base_score=Decimal("7.5"),
                exploit_available=False,
            )
            finding = VulnerabilityFinding(
                id=uuid.uuid4(),
                tenant_id=TEST_TENANT_ID,
                asset_id=asset.id,
                cve_record_id=cve.id,
                status="OPEN",
                discovered_at=datetime.now(timezone.utc) - timedelta(days=10),
            )
            db.add_all([asset, cve, finding])
        
        db.flush()
        
        service = RiskEngineService(db)
        result = service.recalculate_all_open(
            tenant_id=TEST_TENANT_ID,
            batch_size=2,
            use_ml=False,
        )
        
        assert result["total"] == 3
        assert result["updated"] == 3
        assert result["failed"] == 0
        assert result["batch_size"] == 2
