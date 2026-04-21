"""Optional integration checks against a real PostgreSQL instance."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


def _get_postgres_engine():
    """Get PostgreSQL engine or skip if not configured/unavailable."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        pytest.skip("DATABASE_URL not set")
    if "postgresql" not in url.lower():
        pytest.skip("Test requires PostgreSQL")
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


@pytest.mark.integration
def test_database_url_connects():
    engine = _get_postgres_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as e:
        pytest.skip(f"PostgreSQL not reachable: {e}")
    finally:
        engine.dispose()


@pytest.mark.integration
def test_reporting_schema_objects_exist():
    engine = _get_postgres_engine()
    try:
        with engine.connect() as conn:
            n = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'reporting'
                      AND table_name = 'fact_vulnerability_snapshot'
                    """
                )
            ).scalar_one()
        assert int(n) == 1
    except OperationalError as e:
        pytest.skip(f"PostgreSQL not reachable: {e}")
    finally:
        engine.dispose()
