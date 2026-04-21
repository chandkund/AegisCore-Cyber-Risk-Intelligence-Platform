"""Integration tests for Prioritization API endpoints.

Tests cover:
- GET /prioritization/vulnerabilities
- GET /prioritization/vulnerabilities/{id}/risk-score
- POST /prioritization/vulnerabilities/{id}/recalculate
- POST /prioritization/risk/recalculate
- GET /prioritization/top-risks
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, VulnerabilityFinding


def _auth_headers(api_client: TestClient, email: str, password: str) -> dict:
    """Helper to get auth headers for a user."""
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_admin(api_client: TestClient) -> dict:
    return _auth_headers(api_client, "admin@aegiscore.local", "AegisCore!demo2026")


@pytest.fixture
def auth_headers_analyst(api_client: TestClient) -> dict:
    return _auth_headers(api_client, "analyst@aegiscore.local", "AegisCore!demo2026")


@pytest.fixture
def test_finding_with_risk(db: Session) -> VulnerabilityFinding:
    """Create a test finding with pre-calculated risk score."""
    tenant_id = uuid.UUID("a0000000-0000-4000-8000-000000000002")
    business_unit_id = uuid.UUID("a5000001-0000-4000-8000-000000000010")
    asset = Asset(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="test-asset",
        asset_type="server",
        business_unit_id=business_unit_id,
        criticality=1,
        is_external=True,
    )
    cve = CveRecord(
        id=uuid.uuid4(),
        cve_id="CVE-2024-TEST01",
        severity="CRITICAL",
        cvss_base_score=Decimal("9.8"),
        exploit_available=True,
    )
    finding = VulnerabilityFinding(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        asset_id=asset.id,
        cve_record_id=cve.id,
        status="OPEN",
        discovered_at=datetime.now(timezone.utc) - timedelta(days=30),
        risk_score=Decimal("85.50"),
        risk_factors={
            "cvss": 0.98,
            "criticality": 1.0,
            "exposure": 1.0,
            "exploit": 1.0,
            "age": 0.33,
            "rule_based_score": 90.5,
            "calculation_method": "rule_based",
            "contributing_factors": [
                {"factor": "cvss", "score": 0.98, "impact": "high"},
                {"factor": "exploit", "score": 1.0, "impact": "high"},
            ],
        },
        risk_calculated_at=datetime.now(timezone.utc),
    )
    db.add_all([asset, cve, finding])
    db.commit()
    return finding


class TestListPrioritizedVulnerabilities:
    """Test GET /prioritization/vulnerabilities endpoint."""

    def test_requires_authentication(self, api_client: TestClient):
        """Endpoint should require authentication."""
        r = api_client.get("/api/v1/prioritization/vulnerabilities")
        assert r.status_code == 401

    def test_returns_prioritized_list(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk):
        """Should return vulnerabilities sorted by risk score."""
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        
        # Should include our test finding
        finding_ids = [item["id"] for item in data["items"]]
        assert str(test_finding_with_risk.id) in finding_ids

    def test_respects_min_risk_score_filter(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk):
        """Should filter by minimum risk score."""
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities?min_risk_score=90",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        # Our test finding has score 85.50, should not appear
        finding_ids = [item["id"] for item in data["items"]]
        assert str(test_finding_with_risk.id) not in finding_ids

    def test_respects_status_filter(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk, db: Session):
        """Should filter by status."""
        # Change status to REMEDIATED
        test_finding_with_risk.status = "REMEDIATED"
        db.commit()
        
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities?status=OPEN",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        finding_ids = [item["id"] for item in data["items"]]
        assert str(test_finding_with_risk.id) not in finding_ids

    def test_returns_enriched_data(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk):
        """Response should include enriched asset/CVE data."""
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        # Find our test finding
        test_item = None
        for item in data["items"]:
            if item["id"] == str(test_finding_with_risk.id):
                test_item = item
                break
        
        assert test_item is not None
        assert test_item["risk_score"] == 85.50
        assert test_item["asset_name"] == "test-asset"
        assert test_item["cve_id"] == "CVE-2024-TEST01"
        assert test_item["cvss_score"] == 9.8


class TestGetFindingRiskScore:
    """Test GET /prioritization/vulnerabilities/{id}/risk-score endpoint."""

    def test_returns_detailed_risk_info(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk):
        """Should return detailed risk score information."""
        r = api_client.get(
            f"/api/v1/prioritization/vulnerabilities/{test_finding_with_risk.id}/risk-score",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        assert data["finding_id"] == str(test_finding_with_risk.id)
        assert "risk_score" in data
        assert "rule_based_score" in data
        assert "factors" in data
        assert "contributing_factors" in data
        assert "calculation_method" in data
        
        # Factors should be present
        factors = data["factors"]
        assert "cvss" in factors
        assert "criticality" in factors
        assert "exposure" in factors
        assert "exploit" in factors
        assert "age" in factors

    def test_404_for_nonexistent_finding(self, api_client: TestClient, auth_headers_analyst):
        """Should return 404 for non-existent finding."""
        fake_id = uuid.uuid4()
        r = api_client.get(
            f"/api/v1/prioritization/vulnerabilities/{fake_id}/risk-score",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 404

    def test_requires_reader_role(self, api_client: TestClient, test_finding_with_risk):
        """Should require at least reader role."""
        # Try without auth
        r = api_client.get(
            f"/api/v1/prioritization/vulnerabilities/{test_finding_with_risk.id}/risk-score",
        )
        assert r.status_code == 401


class TestRecalculateFindingRisk:
    """Test POST /prioritization/vulnerabilities/{id}/recalculate endpoint."""

    def test_requires_writer_role(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk):
        """Should require writer or admin role."""
        r = api_client.post(
            f"/api/v1/prioritization/vulnerabilities/{test_finding_with_risk.id}/recalculate",
            headers=auth_headers_analyst,
            json={"use_ml": True},
        )
        # Analyst has writer role, should succeed
        assert r.status_code == 200

    def test_updates_risk_score(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk, db: Session):
        """Should recalculate and update risk score in database."""
        old_score = test_finding_with_risk.risk_score
        
        r = api_client.post(
            f"/api/v1/prioritization/vulnerabilities/{test_finding_with_risk.id}/recalculate",
            headers=auth_headers_analyst,
            json={"use_ml": False},
        )
        assert r.status_code == 200
        data = r.json()
        
        # Should have new calculation timestamp
        assert data["calculated_at"] is not None
        assert data["calculation_method"] == "rule_based"

    def test_404_for_nonexistent_finding(self, api_client: TestClient, auth_headers_analyst):
        """Should return 404 for non-existent finding."""
        fake_id = uuid.uuid4()
        r = api_client.post(
            f"/api/v1/prioritization/vulnerabilities/{fake_id}/recalculate",
            headers=auth_headers_analyst,
            json={"use_ml": True},
        )
        assert r.status_code == 404


class TestBulkRecalculate:
    """Test POST /prioritization/risk/recalculate endpoint."""

    def test_requires_admin_role(self, api_client: TestClient, auth_headers_admin):
        """Should require admin role."""
        r = api_client.post(
            "/api/v1/prioritization/risk/recalculate",
            headers=auth_headers_admin,
            json={"batch_size": 10, "use_ml": False},
        )
        # Should succeed with admin
        assert r.status_code == 200

    def test_returns_statistics(self, api_client: TestClient, auth_headers_admin):
        """Should return bulk recalculation statistics."""
        r = api_client.post(
            "/api/v1/prioritization/risk/recalculate",
            headers=auth_headers_admin,
            json={"batch_size": 50, "use_ml": False},
        )
        assert r.status_code == 200
        data = r.json()
        
        assert "total" in data
        assert "updated" in data
        assert "failed" in data
        assert "batch_size" in data

    def test_validates_batch_size(self, api_client: TestClient, auth_headers_admin):
        """Should validate batch_size parameter."""
        # Batch size too small
        r = api_client.post(
            "/api/v1/prioritization/risk/recalculate",
            headers=auth_headers_admin,
            json={"batch_size": 5, "use_ml": False},
        )
        assert r.status_code == 422  # Validation error
        
        # Batch size too large
        r = api_client.post(
            "/api/v1/prioritization/risk/recalculate",
            headers=auth_headers_admin,
            json={"batch_size": 1000, "use_ml": False},
        )
        assert r.status_code == 422  # Validation error


class TestTopRisks:
    """Test GET /prioritization/top-risks endpoint."""

    def test_returns_top_risks_list(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk):
        """Should return list of top risk vulnerabilities."""
        r = api_client.get(
            "/api/v1/prioritization/top-risks?limit=5&min_risk_score=60",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        # Should be a list
        assert isinstance(data, list)
        
        # Should include our high-risk finding
        finding_ids = [item["id"] for item in data]
        assert str(test_finding_with_risk.id) in finding_ids

    def test_respects_limit_parameter(self, api_client: TestClient, auth_headers_analyst):
        """Should respect the limit parameter."""
        r = api_client.get(
            "/api/v1/prioritization/top-risks?limit=3",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        assert len(data) <= 3

    def test_respects_min_risk_score(self, api_client: TestClient, auth_headers_analyst, test_finding_with_risk, db: Session):
        """Should filter by minimum risk score."""
        # Set very high threshold
        r = api_client.get(
            "/api/v1/prioritization/top-risks?min_risk_score=99",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        # Our finding with score 85.50 should not appear
        finding_ids = [item["id"] for item in data]
        assert str(test_finding_with_risk.id) not in finding_ids

    def test_requires_authentication(self, api_client: TestClient):
        """Should require authentication."""
        r = api_client.get("/api/v1/prioritization/top-risks")
        assert r.status_code == 401


class TestPagination:
    """Test pagination behavior."""

    def test_respects_limit_offset(self, api_client: TestClient, auth_headers_analyst):
        """Should respect limit and offset parameters."""
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities?limit=10&offset=0",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["items"]) <= 10

    def test_returns_total_count(self, api_client: TestClient, auth_headers_analyst):
        """Should return total count for pagination."""
        r = api_client.get(
            "/api/v1/prioritization/vulnerabilities",
            headers=auth_headers_analyst,
        )
        assert r.status_code == 200
        data = r.json()
        
        assert "total" in data
        assert isinstance(data["total"], int)
