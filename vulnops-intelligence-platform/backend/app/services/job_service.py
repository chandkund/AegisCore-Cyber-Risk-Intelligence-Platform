from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import BackgroundJob
from app.schemas.jobs import JobOut


class JobService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    @staticmethod
    def _to_out(row: BackgroundJob) -> JobOut:
        return JobOut(
            id=str(row.id),
            job_kind=row.job_kind,
            status=row.status,
            payload=row.payload,
            result=row.result,
            created_by_user_id=str(row.created_by_user_id) if row.created_by_user_id else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def enqueue(self, *, job_kind: str, payload: dict, actor_user_id: uuid.UUID | None) -> JobOut:
        row = BackgroundJob(
            tenant_id=self.tenant_id,
            job_kind=job_kind,
            payload=payload,
            status="QUEUED",
            created_by_user_id=actor_user_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_out(row)

    def list_jobs(self, *, limit: int = 50) -> list[JobOut]:
        rows = self.db.execute(
            select(BackgroundJob)
            .where(BackgroundJob.tenant_id == self.tenant_id)
            .order_by(BackgroundJob.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [self._to_out(r) for r in rows]
