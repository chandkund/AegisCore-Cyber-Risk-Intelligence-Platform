"""Load training rows from PostgreSQL via SQLAlchemy (sync)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, text


def _sync_url(url: str) -> str:
    u = url.strip()
    if u.startswith("postgresql+asyncpg"):
        return u.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return u


def fetch_training_records(database_url: str | None = None) -> list[dict[str, Any]]:
    url = database_url or os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    engine = create_engine(_sync_url(url), pool_pre_ping=True)
    sql = text(
        """
        SELECT
            vf.id AS finding_id,
            vf.status AS status,
            vf.discovered_at AS discovered_at,
            vf.due_at AS due_at,
            (vf.assigned_to_user_id IS NOT NULL) AS has_assignee,
            cr.cvss_base_score AS cvss,
            cr.epss_score AS epss,
            cr.exploit_available AS exploit,
            cr.severity AS severity,
            cr.title AS cve_title,
            a.criticality AS asset_criticality,
            a.name AS asset_name,
            a.asset_type AS asset_type
        FROM vulnerability_findings vf
        JOIN cve_records cr ON cr.id = vf.cve_record_id
        JOIN assets a ON a.id = vf.asset_id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [dict(r) for r in rows]


def reference_time() -> datetime:
    return datetime.now(timezone.utc)
