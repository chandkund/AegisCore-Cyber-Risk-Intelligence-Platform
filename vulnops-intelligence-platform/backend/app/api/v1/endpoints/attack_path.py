from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import ReaderDep
from app.db.deps import get_db
from app.schemas.attack_path import BlastRadiusResponse
from app.services.attack_path_service import AttackPathService

router = APIRouter(prefix="/attack-path", tags=["attack-path"])


@router.get("/assets/{asset_id}/blast-radius", response_model=BlastRadiusResponse)
def blast_radius_from_asset(
    principal: ReaderDep,
    asset_id: str,
    max_depth: int = Query(3, ge=1, le=8),
    db: Session = Depends(get_db),
):
    service = AttackPathService(db, tenant_id=principal.tenant_id)
    try:
        result = service.from_asset(asset_id, max_depth=max_depth)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return BlastRadiusResponse(**result.__dict__)


@router.get("/findings/{finding_id}/blast-radius", response_model=BlastRadiusResponse)
def blast_radius_from_finding(
    principal: ReaderDep,
    finding_id: str,
    max_depth: int = Query(3, ge=1, le=8),
    db: Session = Depends(get_db),
):
    service = AttackPathService(db, tenant_id=principal.tenant_id)
    try:
        result = service.from_finding(finding_id, max_depth=max_depth)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return BlastRadiusResponse(**result.__dict__)
