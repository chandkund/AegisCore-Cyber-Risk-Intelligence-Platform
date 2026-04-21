"""Performance tests for AegisCore backend.

Tests:
- Database query performance
- API response times
- Caching effectiveness
- Connection pooling
"""

import time
from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.services.cache_service import CacheService


client = TestClient(app)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Get database session for tests."""
    session = next(get_db())
    try:
        yield session
    finally:
        session.close()


class TestDatabaseQueryPerformance:
    """Test database query performance."""

    def test_findings_list_query_time(self, db_session):
        """Test that findings list query executes quickly."""
        from app.repositories.finding_repository import FindingRepository

        repo = FindingRepository(db_session)
        tenant_id = uuid4()

        start = time.time()
        repo.list_findings(tenant_id=tenant_id, limit=50, offset=0)
        duration = time.time() - start

        # Should complete in under 500ms
        assert duration < 0.5, f"Query took {duration:.2f}s, expected < 0.5s"

    def test_analytics_summary_query_time(self, db_session):
        """Test analytics summary query performance."""
        from app.repositories.analytics_repository import AnalyticsRepository

        repo = AnalyticsRepository(db_session)
        tenant_id = uuid4()

        start = time.time()
        repo.total_open(tenant_id=tenant_id)
        duration = time.time() - start

        # Should complete in under 200ms
        assert duration < 0.2, f"Query took {duration:.2f}s, expected < 0.2s"

    def test_top_assets_query_time(self, db_session):
        """Test top assets query performance."""
        from app.repositories.analytics_repository import AnalyticsRepository

        repo = AnalyticsRepository(db_session)
        tenant_id = uuid4()

        start = time.time()
        repo.top_assets_by_open_findings(tenant_id=tenant_id, limit=20)
        duration = time.time() - start

        # Should complete in under 300ms
        assert duration < 0.3, f"Query took {duration:.2f}s, expected < 0.3s"


class TestCachingPerformance:
    """Test Redis caching effectiveness."""

    def test_cache_hit_faster_than_miss(self, db_session):
        """Test that cache hits are significantly faster than cache misses."""
        from app.services.analytics_service import AnalyticsService

        cache = CacheService()
        tenant_id = uuid4()

        # Clear cache
        cache.invalidate_tenant_cache(tenant_id)

        svc = AnalyticsService(db_session)

        # First call (cache miss)
        start = time.time()
        svc.summary(tenant_id=tenant_id)
        miss_duration = time.time() - start

        # Second call (cache hit)
        start = time.time()
        svc.summary(tenant_id=tenant_id)
        hit_duration = time.time() - start

        # Cache hit should be at least 10x faster
        assert hit_duration < miss_duration / 10, (
            f"Cache hit ({hit_duration:.4f}s) not significantly faster "
            f"than cache miss ({miss_duration:.4f}s)"
        )

    def test_cache_ttl_respected(self):
        """Test that cache entries expire after TTL."""
        import time

        cache = CacheService()
        tenant_id = uuid4()

        # Set cache with 1 second TTL
        cache.set(tenant_id, "test", "key", "value", ttl=1)

        # Should exist immediately
        assert cache.get(tenant_id, "test", "key") == "value"

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired
        assert cache.get(tenant_id, "test", "key") is None


class TestConnectionPooling:
    """Test database connection pooling."""

    def test_connection_reuse(self):
        """Test that connections are reused from pool."""
        from sqlalchemy import text

        results = []
        for _ in range(20):
            with get_db() as db:
                result = db.execute(text("SELECT pg_backend_pid()"))
                pid = result.scalar()
                results.append(pid)

        # Most connections should be the same (reused)
        unique_pids = set(results)
        reuse_ratio = len(results) / len(unique_pids)

        # Should reuse connections significantly
        assert reuse_ratio > 2, (
            f"Connection reuse ratio {reuse_ratio:.1f} is too low. "
            f"Expected > 2, got {len(unique_pids)} unique PIDs for {len(results)} queries"
        )


class TestAPIResponseTimes:
    """Test API endpoint response times."""

    def test_health_endpoint_speed(self):
        """Test health check endpoint is fast."""
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.1, f"Health check took {duration:.2f}s, expected < 0.1s"

    def test_dashboard_data_endpoint_speed(self, db_session):
        """Test dashboard data endpoint performance."""
        from unittest.mock import patch

        # Mock auth
        with patch("app.api.deps.get_current_principal") as mock_auth:
            mock_auth.return_value = type(
                "MockUser",
                (),
                {
                    "id": uuid4(),
                    "tenant_id": uuid4(),
                    "role": "ADMIN",
                    "is_platform_owner": False,
                },
            )

            start = time.time()
            response = client.get("/api/v1/analytics/summary")
            duration = time.time() - start

            # Should respond in under 1 second (including network)
            assert duration < 1.0, (
                f"Dashboard endpoint took {duration:.2f}s, expected < 1.0s"
            )


class TestPaginationPerformance:
    """Test pagination doesn't degrade with offset."""

    def test_pagination_offset_performance(self, db_session):
        """Test that pagination performance doesn't degrade with offset."""
        from app.repositories.finding_repository import FindingRepository

        repo = FindingRepository(db_session)
        tenant_id = uuid4()

        # Test different offsets
        offsets = [0, 100, 500, 1000]
        durations = []

        for offset in offsets:
            start = time.time()
            repo.list_findings(tenant_id=tenant_id, limit=50, offset=offset)
            duration = time.time() - start
            durations.append(duration)

        # Performance shouldn't degrade significantly with offset
        # Last offset should not be more than 5x slower than first
        assert durations[-1] < durations[0] * 5, (
            f"Pagination degraded from {durations[0]:.3f}s at offset 0 "
            f"to {durations[-1]:.3f}s at offset {offsets[-1]}"
        )


class TestBulkOperations:
    """Test bulk operation performance."""

    def test_bulk_insert_performance(self, db_session):
        """Test bulk insert operations are efficient."""
        from sqlalchemy import text

        # Create test data
        data = [
            {"id": str(uuid4()), "name": f"Test {i}"}
            for i in range(100)
        ]

        start = time.time()
        # Execute bulk insert
        db_session.execute(
            text(
                """
                INSERT INTO test_bulk (id, name)
                VALUES (:id, :name)
                ON CONFLICT DO NOTHING
                """
            ),
            data,
        )
        duration = time.time() - start

        # Should complete in under 1 second
        assert duration < 1.0, f"Bulk insert took {duration:.2f}s for 100 rows"


# Benchmark thresholds
BENCHMARK_CONFIG = {
    "db_query_max_ms": 500,
    "api_response_max_ms": 1000,
    "cache_hit_max_ms": 10,
    "health_check_max_ms": 100,
}
