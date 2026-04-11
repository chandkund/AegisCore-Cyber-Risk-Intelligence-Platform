from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.oltp import Asset


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_assets(
        self,
        *,
        limit: int,
        offset: int,
        business_unit_id: uuid.UUID | None = None,
        search: str | None = None,
        is_active: bool | None = True,
    ) -> tuple[Sequence[Asset], int]:
        id_subq = select(Asset.id)
        list_stmt = select(Asset)
        if business_unit_id:
            id_subq = id_subq.where(Asset.business_unit_id == business_unit_id)
            list_stmt = list_stmt.where(Asset.business_unit_id == business_unit_id)
        if is_active is not None:
            id_subq = id_subq.where(Asset.is_active == is_active)
            list_stmt = list_stmt.where(Asset.is_active == is_active)
        if search:
            like = f"%{search}%"
            cond = or_(
                Asset.name.ilike(like),
                Asset.hostname.ilike(like),
                Asset.ip_address.ilike(like),
            )
            id_subq = id_subq.where(cond)
            list_stmt = list_stmt.where(cond)
        total = int(self.db.scalar(select(func.count()).select_from(id_subq.subquery())) or 0)
        list_stmt = list_stmt.order_by(Asset.name.asc()).offset(offset).limit(limit)
        rows = self.db.execute(list_stmt).scalars().all()
        return rows, total

    def get_by_id(self, asset_id: uuid.UUID) -> Asset | None:
        return self.db.get(Asset, asset_id)

    def create(self, row: Asset) -> Asset:
        self.db.add(row)
        self.db.flush()
        self.db.refresh(row)
        return row
