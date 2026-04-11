from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.oltp import CveRecord


class CveRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_cves(
        self, *, limit: int, offset: int, severity: str | None = None, search: str | None = None
    ) -> tuple[Sequence[CveRecord], int]:
        id_subq = select(CveRecord.id)
        list_stmt = select(CveRecord)
        if severity:
            id_subq = id_subq.where(CveRecord.severity == severity)
            list_stmt = list_stmt.where(CveRecord.severity == severity)
        if search:
            like = f"%{search}%"
            cond = or_(CveRecord.cve_id.ilike(like), CveRecord.title.ilike(like))
            id_subq = id_subq.where(cond)
            list_stmt = list_stmt.where(cond)
        total = int(self.db.scalar(select(func.count()).select_from(id_subq.subquery())) or 0)
        list_stmt = list_stmt.order_by(CveRecord.cve_id.asc()).offset(offset).limit(limit)
        rows = self.db.execute(list_stmt).scalars().all()
        return rows, total

    def get_by_id(self, cve_pk: uuid.UUID) -> CveRecord | None:
        return self.db.get(CveRecord, cve_pk)

    def get_by_cve_id(self, cve_id: str) -> CveRecord | None:
        return self.db.execute(
            select(CveRecord).where(CveRecord.cve_id == cve_id.strip())
        ).scalar_one_or_none()
