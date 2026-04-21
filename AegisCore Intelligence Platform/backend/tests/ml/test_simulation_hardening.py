"""Security and functionality hardening tests for what-if simulation feature.

These tests verify:
- Invalid asset IDs are rejected
- Duplicate IDs are handled
- Empty selection is handled
- Tenant-safe computation
- Depth limits enforced
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.oltp import Asset, Company

pytestmark = pytest.mark.skip(reason="Legacy benchmark suite: superseded by tenant-aware integration/security gates")

client = TestClient(app)


class TestSimulationSecurity:
    """Simulation security tests."""

    def test_cross_tenant_simulation_blocked(
        self, db: Session, test_company: Company, other_company: Company
    ):
        """Can't simulate with another tenant's assets."""
        # Create asset in other company
        asset = Asset(
            id=uuid.uuid4(),
            company_id=other_company.id,
            tenant_id=other_company.id,
            name="Other Company Asset",
            asset_type="server",
        )
        db.add(asset)
        db.commit()
        
        # Try to simulate including other company's asset
        response = client.post(
            "/api/v1/simulation/run",
            json={
                "target_asset_ids": [str(asset.id)],
                "simulation_depth": 3,
            },
        )
        
        # Should be blocked
        assert response.status_code in [403, 404]

    def test_invalid_asset_ids_rejected(self, db: Session, company_headers: dict):
        """Non-existent asset IDs should be rejected."""
        fake_id = uuid.uuid4()
        
        response = client.post(
            "/api/v1/simulation/run",
            headers=company_headers,
            json={
                "target_asset_ids": [str(fake_id)],
                "simulation_depth": 3,
            },
        )
        
        # Should error - asset not found
        assert response.status_code in [400, 404, 422]

    def test_malformed_uuid_rejected(self, db: Session, company_headers: dict):
        """Malformed UUIDs should be rejected."""
        response = client.post(
            "/api/v1/simulation/run",
            headers=company_headers,
            json={
                "target_asset_ids": ["not-a-uuid", "123", ""],
                "simulation_depth": 3,
            },
        )
        
        assert response.status_code == 422  # Validation error

    def test_excessive_depth_rejected(self, db: Session, test_company: Company):
        """Very deep simulation should be rejected or limited."""
        # Create an asset
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            asset_type="server",
        )
        db.add(asset)
        db.commit()
        
        # Request excessive depth
        response = client.post(
            "/api/v1/simulation/run",
            json={
                "target_asset_ids": [str(asset.id)],
                "simulation_depth": 100,  # Too deep
            },
        )
        
        # Should either reject or clamp
        if response.status_code == 200:
            data = response.json()
            # Should indicate depth was limited
            assert data.get("depth") <= 10
        else:
            assert response.status_code == 422


class TestSimulationFunctionality:
    """Simulation functionality tests."""

    def test_duplicate_ids_deduplicated(self, db: Session, test_company: Company):
        """Duplicate IDs should be handled gracefully."""
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            asset_type="server",
        )
        db.add(asset)
        db.commit()
        
        # Send duplicate IDs
        response = client.post(
            "/api/v1/simulation/run",
            json={
                "target_asset_ids": [
                    str(asset.id),
                    str(asset.id),
                    str(asset.id),
                ],
                "simulation_depth": 3,
            },
        )
        
        # Should succeed (deduplicated)
        assert response.status_code in [200, 202]

    def test_empty_selection_handled(self, db: Session, company_headers: dict):
        """Empty asset list should return empty result."""
        response = client.post(
            "/api/v1/simulation/run",
            headers=company_headers,
            json={
                "target_asset_ids": [],
                "simulation_depth": 3,
            },
        )
        
        # Should succeed with empty result
        assert response.status_code == 200
        data = response.json()
        assert data.get("paths", data.get("results", [])) == []

    def test_simulation_returns_paths(self, db: Session, test_company: Company):
        """Simulation should return attack paths."""
        # Create interconnected assets
        asset1 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Web Server",
            asset_type="server",
        )
        asset2 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Database",
            asset_type="database",
        )
        db.add_all([asset1, asset2])
        db.commit()
        
        # Run simulation
        response = client.post(
            "/api/v1/simulation/run",
            json={
                "target_asset_ids": [str(asset1.id)],
                "simulation_depth": 3,
            },
        )
        
        # Should return results
        assert response.status_code in [200, 202]
        if response.status_code == 200:
            data = response.json()
            # Should have paths structure
            assert "paths" in data or "results" in data

    def test_simulation_depth_affects_results(self, db: Session, test_company: Company):
        """Deeper simulation should find more paths."""
        # Create chain of assets
        assets = []
        for i in range(5):
            asset = Asset(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                name=f"Asset {i}",
                asset_type="server",
            )
            assets.append(asset)
            db.add(asset)
        db.commit()
        
        # Run with different depths
        depths = [1, 2, 3]
        results = []
        
        for depth in depths:
            response = client.post(
                "/api/v1/simulation/run",
                json={
                    "target_asset_ids": [str(assets[0].id)],
                    "simulation_depth": depth,
                },
            )
            if response.status_code == 200:
                data = response.json()
                paths = data.get("paths", data.get("results", []))
                results.append(len(paths))
        
        # Deeper should generally find more (or equal)
        for i in range(len(results) - 1):
            assert results[i + 1] >= results[i]


class TestSimulationConsistency:
    """Simulation consistency tests."""

    def test_simulation_is_deterministic(self, db: Session, test_company: Company):
        """Same inputs should produce same simulation results."""
        # Create asset
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Test Asset",
            asset_type="server",
        )
        db.add(asset)
        db.commit()
        
        # Run multiple times
        results = []
        for _ in range(3):
            response = client.post(
                "/api/v1/simulation/run",
                json={
                    "target_asset_ids": [str(asset.id)],
                    "simulation_depth": 3,
                },
            )
            if response.status_code == 200:
                results.append(response.json())
        
        # Results should be identical
        if len(results) > 1:
            for i in range(len(results) - 1):
                # Compare key fields
                assert results[i].get("paths") == results[i + 1].get("paths")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_company(db: Session):
    """Create test company."""
    from app.models.oltp import Company
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
    from app.models.oltp import Company
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
def company_headers(test_company):
    """Get auth headers for company."""
    return {}

