from __future__ import annotations

import uuid

from app.api.deps import ReaderDep, WriterDep
from app.db.deps import get_db
from app.schemas.asset import AssetCreate, AssetOut, AssetUpdate
from app.schemas.common import Paginated
from app.services.asset_service import AssetService
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=Paginated[AssetOut])
def list_assets(
    principal: ReaderDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    business_unit_id: uuid.UUID | None = None,
    q: str | None = Query(None, description="Search name, hostname, IP"),
    is_active: bool | None = Query(True),
):
    items, total = AssetService(db).list_assets(
        tenant_id=principal.tenant_id,
        limit=limit,
        offset=offset,
        business_unit_id=business_unit_id,
        search=q,
        is_active=is_active,
    )
    return Paginated(items=items, total=total, limit=limit, offset=offset)


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(principal: ReaderDep, asset_id: uuid.UUID, db: Session = Depends(get_db)):
    row = AssetService(db).get(asset_id, principal.tenant_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return row


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(principal: WriterDep, body: AssetCreate, db: Session = Depends(get_db)):
    try:
        return AssetService(db).create(body, actor_id=principal.id, tenant_id=principal.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(
    principal: WriterDep,
    asset_id: uuid.UUID,
    body: AssetUpdate,
    db: Session = Depends(get_db),
):
    row = AssetService(db).update(
        asset_id, body, actor_id=principal.id, tenant_id=principal.tenant_id
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return row
