from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import ReaderDep, WriterDep
from app.db.deps import get_db
from app.schemas.jobs import JobCreateRequest, JobOut
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobOut)
def enqueue_job(principal: WriterDep, body: JobCreateRequest, db: Session = Depends(get_db)):
    return JobService(db, tenant_id=principal.tenant_id).enqueue(
        job_kind=body.job_kind,
        payload=body.payload,
        actor_user_id=principal.id,
    )


@router.get("", response_model=list[JobOut])
def list_jobs(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    return JobService(db, tenant_id=principal.tenant_id).list_jobs(limit=limit)
