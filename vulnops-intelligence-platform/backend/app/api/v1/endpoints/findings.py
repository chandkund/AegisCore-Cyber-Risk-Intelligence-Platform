from __future__ import annotations

import uuid

from app.api.deps import AdminDep, ReaderDep, WriterDep
from app.db.deps import get_db
from app.schemas.common import Paginated
from app.schemas.finding import FindingCreate, FindingOut, FindingUpdate
from app.services.finding_service import FindingService
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=Paginated[FindingOut])
def list_findings(
    _: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
    asset_id: uuid.UUID | None = Query(None),
    cve_id: str | None = Query(None, description="Substring match on CVE id"),
    q: str | None = Query(None, description="Search notes, CVE id, title"),
):
    items, total = FindingService(db).list_findings(
        limit=limit,
        offset=offset,
        status=status_filter,
        asset_id=asset_id,
        cve_id_contains=cve_id,
        search=q,
    )
    return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.get("/{finding_id}", response_model=FindingOut)
def get_finding(_: ReaderDep, finding_id: uuid.UUID, db: Session = Depends(get_db)):
    row = FindingService(db).get(finding_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return row


@router.post("", response_model=FindingOut, status_code=status.HTTP_201_CREATED)
def create_finding(principal: WriterDep, body: FindingCreate, db: Session = Depends(get_db)):
    try:
        return FindingService(db).create(body, actor_id=principal.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{finding_id}", response_model=FindingOut)
def update_finding(
    principal: WriterDep,
    finding_id: uuid.UUID,
    body: FindingUpdate,
    db: Session = Depends(get_db),
):
    row = FindingService(db).update(finding_id, body, actor_id=principal.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return row


@router.delete(
    "/{finding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_finding(principal: AdminDep, finding_id: uuid.UUID, db: Session = Depends(get_db)):
    ok = FindingService(db).delete(finding_id, actor_id=principal.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
