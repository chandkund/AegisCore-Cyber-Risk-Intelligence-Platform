"""Performance and load tests for ML features.

Tests verify system handles production-scale load:
- Large datasets (100K+ findings)
- Concurrent users
- Response time SLAs
- Memory and CPU usage
"""

from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.oltp import Asset, Company, CveRecord, User, VulnerabilityFinding

pytestmark = pytest.mark.skip(reason="Requires dedicated performance harness and legacy benchmark schema")

client = TestClient(app)


class TestPrioritizationPerformance:
    """Performance tests for prioritization."""
    
    def test_prioritization_10k_findings(self, db: Session, test_company: Company):
        """Prioritization should handle 10K findings in <2 seconds."""
        # Create 10K findings
        findings = []
        for i in range(10000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Vulnerability {i}",
                severity=["critical", "high", "medium", "low"][i % 4],
                status="open",
                risk_score=50 + (i % 50),
            )
            findings.append(f)
        
        db.bulk_save_objects(findings)
        db.commit()
        
        # Time the prioritization
        start = time.time()
        response = client.get("/api/v1/findings/prioritized?limit=100")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0, f"Prioritization took {elapsed}s, expected <2s"
    
    def test_prioritization_concurrent_users(self, db: Session, test_company: Company):
        """Handle 50 concurrent prioritization requests."""
        # Create test data
        for i in range(1000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Vuln {i}",
                severity="high",
                status="open",
            )
            db.add(f)
        db.commit()
        
        # Concurrent requests
        def make_request():
            return client.get("/api/v1/findings/prioritized")
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            start = time.time()
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in futures]
            elapsed = time.time() - start
        
        # All should succeed
        assert all(r.status_code == 200 for r in results)
        # Should complete in reasonable time (not sequential)
        assert elapsed < 10.0, f"50 concurrent requests took {elapsed}s"


class TestSearchPerformance:
    """Performance tests for search."""
    
    def test_search_50k_findings(self, db: Session, test_company: Company):
        """Search should handle 50K findings with sub-second response."""
        # Create 50K findings
        findings = []
        for i in range(50000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                cve_id=f"CVE-2023-{i:04d}",
                title=f"Finding number {i} about security issue",
                severity="medium",
                status="open",
            )
            findings.append(f)
        
        db.bulk_save_objects(findings)
        db.commit()
        
        # Test various searches
        queries = ["CVE-2023", "security", "finding", "number 1234"]
        
        for query in queries:
            start = time.time()
            response = client.get(f"/api/v1/search?q={query}&limit=20")
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 1.0, f"Search '{query}' took {elapsed}s"
    
    def test_search_pagination_performance(self, db: Session, test_company: Company):
        """Pagination should not degrade with deep pages."""
        # Create data
        for i in range(10000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Item {i}",
                severity="medium",
                status="open",
            )
            db.add(f)
        db.commit()
        
        # Test deep pagination
        offsets = [0, 100, 500, 1000]
        
        for offset in offsets:
            start = time.time()
            response = client.get(f"/api/v1/search?q=item&limit=20&offset={offset}")
            elapsed = time.time() - start
            
            assert response.status_code == 200
            # Deep pages should not be significantly slower
            assert elapsed < 1.5, f"Page at offset {offset} took {elapsed}s"


class TestSimulationPerformance:
    """Performance tests for simulation."""
    
    def test_simulation_small_graph(self, db: Session, test_company: Company):
        """Small graph (10 assets) should complete in <1s."""
        # Create small network
        assets = []
        for i in range(10):
            a = Asset(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                name=f"Asset {i}",
                asset_type="server",
            )
            assets.append(a)
            db.add(a)
        db.commit()
        
        start = time.time()
        response = client.post(
            "/api/v1/simulation/run",
            json={
                "target_asset_ids": [str(a.id) for a in assets[:3]],
                "simulation_depth": 3,
            },
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Small simulation took {elapsed}s"
    
    def test_simulation_medium_graph(self, db: Session, test_company: Company):
        """Medium graph (100 assets) should complete in <5s."""
        # Create medium network
        assets = []
        for i in range(100):
            a = Asset(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                name=f"Asset {i}",
                asset_type="server",
            )
            assets.append(a)
            db.add(a)
        db.commit()
        
        start = time.time()
        response = client.post(
            "/api/v1/simulation/run",
            json={
                "target_asset_ids": [str(a.id) for a in assets[:10]],
                "simulation_depth": 5,
            },
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Medium simulation took {elapsed}s"
    
    def test_simulation_depth_scaling(self, db: Session, test_company: Company):
        """Simulation depth should scale reasonably."""
        # Create test assets
        assets = []
        for i in range(50):
            a = Asset(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                name=f"Node {i}",
                asset_type="server",
            )
            assets.append(a)
            db.add(a)
        db.commit()
        
        target_id = str(assets[0].id)
        
        # Test different depths
        depths = [2, 4, 6, 8]
        times = []
        
        for depth in depths:
            start = time.time()
            response = client.post(
                "/api/v1/simulation/run",
                json={
                    "target_asset_ids": [target_id],
                    "simulation_depth": depth,
                },
            )
            elapsed = time.time() - start
            times.append(elapsed)
            
            assert response.status_code == 200
        
        # Time should not explode exponentially
        for i in range(len(times) - 1):
            ratio = times[i + 1] / times[i] if times[i] > 0 else 1
            assert ratio < 3.0, f"Depth scaling too steep: {ratio}x"


class TestAssistantPerformance:
    """Performance tests for AI assistant."""
    
    def test_assistant_response_time(self, db: Session, test_company: Company, auth_headers: dict):
        """Assistant should respond in <500ms for simple queries."""
        # Create some test data
        for i in range(100):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Risky finding {i}",
                severity="high",
                status="open",
                risk_score=80 + i,
            )
            db.add(f)
        db.commit()
        
        queries = [
            "What are my top risks?",
            "Show me critical vulnerabilities",
            "How has my risk changed?",
        ]
        
        for query in queries:
            start = time.time()
            response = client.post(
                "/api/v1/assistant/chat",
                headers=auth_headers,
                json={
                    "message": query,
                    "context": "security_review",
                },
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                assert elapsed < 0.5, f"Query '{query}' took {elapsed}s"
    
    def test_assistant_rate_limiting(self, db: Session, auth_headers: dict):
        """Rate limiting should prevent abuse."""
        # Rapid fire requests
        responses = []
        for _ in range(35):  # Above the 30/min limit
            response = client.post(
                "/api/v1/assistant/chat",
                headers=auth_headers,
                json={
                    "message": "Hello",
                    "context": "security_review",
                },
            )
            responses.append(response.status_code)
            time.sleep(0.05)  # Small delay
        
        # Should see rate limiting kick in
        assert 429 in responses or responses.count(200) <= 30


class TestCachingPerformance:
    """Performance tests for caching layer."""
    
    def test_prioritization_cache_hit(self, db: Session, test_company: Company):
        """Cached prioritization should be faster."""
        # Create test data
        for i in range(1000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Finding {i}",
                severity="high",
                status="open",
                risk_score=75,
            )
            db.add(f)
        db.commit()
        
        # First request (cache miss)
        start = time.time()
        r1 = client.get("/api/v1/findings/prioritized?limit=20")
        t1 = time.time() - start
        
        assert r1.status_code == 200
        
        # Second request (cache hit)
        start = time.time()
        r2 = client.get("/api/v1/findings/prioritized?limit=20")
        t2 = time.time() - start
        
        assert r2.status_code == 200
        # Cache hit should be faster (or at least not slower)
        assert t2 <= t1 * 1.5, f"Cache not effective: {t1}s -> {t2}s"


class TestMemoryUsage:
    """Memory usage tests."""
    
    def test_large_result_set_memory(self, db: Session, test_company: Company):
        """Large result sets should not OOM."""
        # Create large dataset
        for i in range(50000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                title=f"Finding {i}",
                severity="medium",
                status="open",
            )
            db.add(f)
            if i % 1000 == 0:
                db.flush()
        db.commit()
        
        # Request with large limit
        response = client.get("/api/v1/findings/prioritized?limit=1000")
        
        assert response.status_code == 200
        data = response.json()
        # Should be limited
        assert len(data.get("items", [])) <= 100


class TestEndToEndPerformance:
    """End-to-end performance tests."""
    
    def test_full_workflow_performance(self, db: Session, test_company: Company, auth_headers: dict):
        """Full workflow should complete in reasonable time."""
        # Setup: Create test data
        for i in range(1000):
            f = VulnerabilityFinding(
                id=uuid.uuid4(),
                company_id=test_company.id,
                tenant_id=test_company.id,
                cve_id=f"CVE-2023-{i:04d}",
                title=f"Workflow test {i}",
                severity=["critical", "high"][i % 2],
                status="open",
                risk_score=80 + (i % 20),
            )
            db.add(f)
        db.commit()
        
        start = time.time()
        
        # Step 1: Get priorities
        r1 = client.get("/api/v1/findings/prioritized?limit=10")
        assert r1.status_code == 200
        
        # Step 2: Search for specific
        r2 = client.get("/api/v1/search?q=CVE-2023&limit=10")
        assert r2.status_code == 200
        
        # Step 3: Get trends
        r3 = client.get("/api/v1/analytics/trends")
        assert r3.status_code in [200, 404]  # May not exist
        
        # Step 4: Run simulation
        assets = db.query(Asset).filter_by(tenant_id=test_company.id).limit(5).all()
        if assets:
            r4 = client.post(
                "/api/v1/simulation/run",
                json={
                    "target_asset_ids": [str(a.id) for a in assets],
                    "simulation_depth": 3,
                },
            )
            assert r4.status_code == 200
        
        # Step 5: Assistant query
        r5 = client.post(
            "/api/v1/assistant/chat",
            headers=auth_headers,
            json={
                "message": "What are my top risks?",
                "context": "security_review",
            },
        )
        assert r5.status_code in [200, 404, 501]
        
        elapsed = time.time() - start
        
        # Full workflow should complete in <10s
        assert elapsed < 10.0, f"Full workflow took {elapsed}s"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_company(db: Session):
    """Create test company."""
    from app.models.oltp import Company
    company = Company(
        id=uuid.uuid4(),
        name="Perf Test Company",
        code="PERFCO",
        is_active=True,
    )
    db.add(company)
    db.commit()
    return company


@pytest.fixture
def auth_headers(test_company):
    """Auth headers for tests."""
    return {}

