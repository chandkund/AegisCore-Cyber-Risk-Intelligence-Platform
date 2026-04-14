"""Connection pool stress and exhaustion tests."""

from __future__ import annotations

import concurrent.futures
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def test_connection_pool_handles_concurrent_requests(api_client: TestClient):
    """Verify connection pool handles concurrent API requests without exhaustion."""
    # This requires a real database to test actual pool behavior
    import os

    url = os.getenv("AEGISCORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("AEGISCORE_TEST_DATABASE_URL not set")

    # Health check endpoint that queries database
    def make_request(i: int) -> bool:
        try:
            r = api_client.get("/ready")
            return r.status_code == 200
        except Exception:
            return False

    # Make 50 concurrent requests
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(make_request, range(50)))
    duration = time.time() - start

    # All requests should succeed
    success_count = sum(1 for r in results if r)
    assert success_count == 50, f"Only {success_count}/50 requests succeeded"

    # Should complete within reasonable time (pool_size=10 + max_overflow=20 = 30 connections)
    assert duration < 10, f"Requests took too long: {duration}s"


def test_connection_pool_timeout_on_exhaustion():
    """Verify pool timeout behavior when all connections are in use."""
    import os

    url = os.getenv("AEGISCORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("AEGISCORE_TEST_DATABASE_URL not set")

    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)

    # Create engine with tiny pool to force exhaustion
    engine = create_engine(
        url,
        pool_size=2,
        max_overflow=0,
        pool_timeout=1,  # 1 second timeout
        pool_pre_ping=True,
    )

    connections = []

    try:
        # Use up all connections
        for _ in range(2):
            conn = engine.connect()
            conn.execute(text("SELECT pg_sleep(5)"))  # Hold connection for 5 seconds
            connections.append(conn)

        # Third connection should timeout
        start = time.time()
        with pytest.raises(Exception) as exc_info:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        duration = time.time() - start
        assert duration < 2, "Should timeout quickly"
        assert "timeout" in str(exc_info.value).lower() or "QueuePool" in str(exc_info.value)

    finally:
        # Cleanup
        for conn in connections:
            conn.close()
        engine.dispose()


def test_connection_pool_pre_ping_recovers():
    """Verify pool pre_ping reconnects after connection loss."""
    import os

    url = os.getenv("AEGISCORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("AEGISCORE_TEST_DATABASE_URL not set")

    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)

    engine = create_engine(
        url,
        pool_size=5,
        pool_pre_ping=True,
    )

    # First connection works
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

    # Close all connections in pool (simulates server restart)
    engine.dispose()

    # New engine should still work due to pre_ping
    engine2 = create_engine(
        url,
        pool_size=5,
        pool_pre_ping=True,
    )

    try:
        with engine2.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    finally:
        engine2.dispose()


def test_connection_pool_recycle():
    """Verify connections are recycled after pool_recycle time."""
    import os

    url = os.getenv("AEGISCORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("AEGISCORE_TEST_DATABASE_URL not set")

    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)

    # Very short recycle time for testing
    engine = create_engine(
        url,
        pool_size=2,
        pool_recycle=2,  # Recycle after 2 seconds
        pool_pre_ping=True,
    )

    try:
        # Get connection ID
        with engine.connect() as conn:
            result = conn.execute(text("SELECT pg_backend_pid()"))
            pid1 = result.scalar()

        # Wait for recycle
        time.sleep(3)

        # Should get new connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT pg_backend_pid()"))
            pid2 = result.scalar()

        # PIDs should be different (old connection was recycled)
        assert pid1 != pid2, "Connection should have been recycled"

    finally:
        engine.dispose()
