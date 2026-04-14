"""Optional integration checks against a real PostgreSQL instance."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_database_url_connects():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        pytest.skip("DATABASE_URL not set")
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    engine.dispose()


@pytest.mark.integration
def test_reporting_schema_objects_exist():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        pytest.skip("DATABASE_URL not set")
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    engine = create_engine(url, pool_pre_ping=True)
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
    engine.dispose()
    assert int(n) == 1
