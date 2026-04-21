from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from pathlib import Path

from app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        db_url = get_settings().database_url_sync
        settings = get_settings()
        # SQLite uses different pool and connection settings
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                connect_args={"check_same_thread": False},
            )
        else:
            # PostgreSQL settings
            # Production-grade connection pooling
            # pool_size: Default connections maintained
            # max_overflow: Extra connections allowed when pool is exhausted
            # pool_timeout: Seconds to wait for available connection
            # pool_recycle: Recycle connections after 30 minutes to prevent stale connections
            candidate = create_engine(
                db_url,
                pool_pre_ping=True,  # Verify connections before use
                pool_size=20,  # Base pool size for concurrent requests
                max_overflow=30,  # Allow burst up to 50 total connections
                pool_timeout=30,  # Wait up to 30s for available connection
                pool_recycle=1800,  # Recycle after 30 minutes
                pool_use_lifo=True,  # LIFO for better connection reuse
                connect_args={
                    "connect_timeout": 10,  # Connection establishment timeout
                    "options": "-c statement_timeout=30000",  # 30s query timeout
                },
            )
            # Test-only fallback: when local Postgres is unavailable, use SQLite
            # so automated tests can still run deterministically.
            allow_sqlite_fallback = os.getenv("AEGISCORE_TEST_MODE", "").lower() in {
                "1",
                "true",
                "yes",
            }
            if settings.app_env not in {"production", "staging"} and allow_sqlite_fallback:
                try:
                    with candidate.connect() as conn:
                        conn.exec_driver_sql("SELECT 1")
                except Exception:
                    sqlite_path = Path("./.pytest_runtime.db")
                    if sqlite_path.exists():
                        sqlite_path.unlink()
                    candidate = create_engine(
                        f"sqlite:///{sqlite_path.as_posix()}",
                        pool_pre_ping=True,
                        connect_args={"check_same_thread": False},
                    )
                    # Bootstrap minimal local schema for test/dev fallback.
                    from app import models  # noqa: F401
                    from app.db.base import Base

                    local_tables = [
                        table for table in Base.metadata.tables.values() if not table.schema
                    ]
                    Base.metadata.create_all(candidate, tables=local_tables)
                    with candidate.begin() as conn:
                        conn.exec_driver_sql(
                            "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)"
                        )
            _engine = candidate
    return _engine


# Backward-compatible module attribute used by older tests/imports.
engine = get_engine()


def reset_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)


def get_db():
    """Compatibility dependency used by API routes and older tests."""
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
