from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.oltp import CveRecord, VulnerabilityFinding


class FindingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_findings(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None = None,
        asset_id: uuid.UUID | None = None,
        cve_id_contains: str | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[VulnerabilityFinding], int]:
        id_subq = select(VulnerabilityFinding.id)
        list_stmt = select(VulnerabilityFinding)

        if status:
            id_subq = id_subq.where(VulnerabilityFinding.status == status)
            list_stmt = list_stmt.where(VulnerabilityFinding.status == status)
        if asset_id:
            id_subq = id_subq.where(VulnerabilityFinding.asset_id == asset_id)
            list_stmt = list_stmt.where(VulnerabilityFinding.asset_id == asset_id)

        if cve_id_contains or search:
            id_subq = id_subq.join(CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id)
            list_stmt = list_stmt.join(
                CveRecord, VulnerabilityFinding.cve_record_id == CveRecord.id
            )
            if cve_id_contains:
                id_subq = id_subq.where(CveRecord.cve_id.ilike(f"%{cve_id_contains}%"))
                list_stmt = list_stmt.where(CveRecord.cve_id.ilike(f"%{cve_id_contains}%"))
            if search:
                like = f"%{search}%"
                cond = or_(
                    VulnerabilityFinding.notes.ilike(like),
                    CveRecord.cve_id.ilike(like),
                    CveRecord.title.ilike(like),
                )
                id_subq = id_subq.where(cond)
                list_stmt = list_stmt.where(cond)

        total = int(self.db.scalar(select(func.count()).select_from(id_subq.subquery())) or 0)
        list_stmt = list_stmt.order_by(VulnerabilityFinding.discovered_at.desc())
        list_stmt = list_stmt.offset(offset).limit(limit)
        rows = self.db.execute(list_stmt).scalars().all()
        return rows, total

    def get_by_id(self, finding_id: uuid.UUID) -> VulnerabilityFinding | None:
        return self.db.get(VulnerabilityFinding, finding_id)

    def create(self, row: VulnerabilityFinding) -> VulnerabilityFinding:
        self.db.add(row)
        self.db.flush()
        self.db.refresh(row)
        return row

    def delete(self, row: VulnerabilityFinding) -> None:
        self.db.delete(row)
        self.db.flush()
