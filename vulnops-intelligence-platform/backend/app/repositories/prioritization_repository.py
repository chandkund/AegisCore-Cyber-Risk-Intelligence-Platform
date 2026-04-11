from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class PrioritizationRepository:
    """Read-only joins for ML feature extraction."""

    def __init__(self, db: Session):
        self.db = db

    def get_finding_feature_row(self, finding_id: uuid.UUID) -> dict[str, Any] | None:
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
            WHERE vf.id = :fid
            """
        )
        row = self.db.execute(sql, {"fid": finding_id}).mappings().first()
        return dict(row) if row else None
