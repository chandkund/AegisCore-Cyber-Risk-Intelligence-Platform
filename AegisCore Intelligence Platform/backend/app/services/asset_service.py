from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.oltp import Asset
from app.repositories.asset_repository import AssetRepository
from app.schemas.asset import AssetCreate, AssetOut, AssetUpdate
from app.services.audit_service import AuditService


class AssetService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssetRepository(db)
        self.audit = AuditService(db)

    def to_out(self, a: Asset) -> AssetOut:
        return AssetOut(
            id=str(a.id),
            name=a.name,
            asset_type=a.asset_type,
            hostname=a.hostname,
            ip_address=a.ip_address,
            business_unit_id=str(a.business_unit_id),
            team_id=str(a.team_id) if a.team_id else None,
            location_id=str(a.location_id) if a.location_id else None,
            criticality=int(a.criticality),
            owner_email=a.owner_email,
            is_active=a.is_active,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )

    def list_assets(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int,
        offset: int,
        business_unit_id: uuid.UUID | None,
        search: str | None,
        is_active: bool | None,
    ) -> tuple[list[AssetOut], int]:
        rows, total = self.repo.list_assets(
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
            business_unit_id=business_unit_id,
            search=search,
            is_active=is_active,
        )
        return [self.to_out(a) for a in rows], total

    def get(self, asset_id: uuid.UUID, tenant_id: uuid.UUID) -> AssetOut | None:
        a = self.repo.get_by_id(asset_id, tenant_id=tenant_id)
        return self.to_out(a) if a else None

    def create(self, data: AssetCreate, *, actor_id: uuid.UUID | None, tenant_id: uuid.UUID) -> AssetOut:
        row = Asset(
            tenant_id=tenant_id,
            name=data.name.strip(),
            asset_type=data.asset_type.strip(),
            hostname=data.hostname.strip() if data.hostname else None,
            ip_address=data.ip_address.strip() if data.ip_address else None,
            business_unit_id=uuid.UUID(data.business_unit_id),
            team_id=uuid.UUID(data.team_id) if data.team_id else None,
            location_id=uuid.UUID(data.location_id) if data.location_id else None,
            criticality=data.criticality,
            owner_email=data.owner_email.strip() if data.owner_email else None,
            is_active=data.is_active,
        )
        self.repo.create(row)
        self.audit.record(
            actor_user_id=actor_id,
            action="asset.create",
            resource_type="asset",
            resource_id=str(row.id),
        )
        self.db.commit()
        self.db.refresh(row)
        return self.to_out(row)

    def update(
        self,
        asset_id: uuid.UUID,
        data: AssetUpdate,
        *,
        actor_id: uuid.UUID | None,
        tenant_id: uuid.UUID,
    ) -> AssetOut | None:
        a = self.repo.get_by_id(asset_id, tenant_id=tenant_id)
        if not a:
            return None
        patch = data.model_dump(exclude_unset=True)
        if "name" in patch:
            a.name = patch["name"].strip()
        if "asset_type" in patch:
            a.asset_type = patch["asset_type"].strip()
        if "hostname" in patch:
            v = patch["hostname"]
            a.hostname = v.strip() if v else None
        if "ip_address" in patch:
            v = patch["ip_address"]
            a.ip_address = v.strip() if v else None
        if "business_unit_id" in patch and patch["business_unit_id"]:
            a.business_unit_id = uuid.UUID(patch["business_unit_id"])
        if "team_id" in patch:
            v = patch["team_id"]
            a.team_id = uuid.UUID(v) if v else None
        if "location_id" in patch:
            v = patch["location_id"]
            a.location_id = uuid.UUID(v) if v else None
        if "criticality" in patch and patch["criticality"] is not None:
            a.criticality = patch["criticality"]
        if "owner_email" in patch:
            v = patch["owner_email"]
            a.owner_email = v.strip() if v else None
        if "is_active" in patch and patch["is_active"] is not None:
            a.is_active = patch["is_active"]
        self.db.flush()
        self.audit.record(
            actor_user_id=actor_id,
            action="asset.update",
            resource_type="asset",
            resource_id=str(a.id),
            payload={"fields": list(patch.keys())},
        )
        self.db.commit()
        self.db.refresh(a)
        return self.to_out(a)
