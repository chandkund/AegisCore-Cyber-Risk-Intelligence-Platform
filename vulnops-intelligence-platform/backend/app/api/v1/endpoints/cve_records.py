from __future__ import annotations

import uuid

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.models.oltp import CveRecord
from app.repositories.cve_repository import CveRepository
from app.schemas.common import Paginated
from app.schemas.cve import CveRecordOut
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/cve-records", tags=["cve-records"])


def _to_out(c: CveRecord) -> CveRecordOut:
    return CveRecordOut(
        id=str(c.id),
        cve_id=c.cve_id,
        title=c.title,
        description=c.description,
        published_at=c.published_at,
        last_modified_at=c.last_modified_at,
        cvss_base_score=c.cvss_base_score,
        cvss_vector=c.cvss_vector,
        severity=c.severity,
        epss_score=c.epss_score,
        exploit_available=c.exploit_available,
    )


@router.get("", response_model=Paginated[CveRecordOut])
def list_cve_records(
    _: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    severity: str | None = None,
    q: str | None = Query(None, description="Search CVE id or title"),
):
    rows, total = CveRepository(db).list_cves(
        limit=limit, offset=offset, severity=severity, search=q
    )
    return Paginated(
        items=[_to_out(c) for c in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{cve_pk}", response_model=CveRecordOut)
def get_cve_record(_: ReaderDep, cve_pk: uuid.UUID, db: Session = Depends(get_db)):
    c = CveRepository(db).get_by_id(cve_pk)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CVE record not found")
    return _to_out(c)
