from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import Asset, CveRecord, VulnerabilityFinding
from app.repositories.cve_repository import CveRepository
from app.repositories.finding_repository import FindingRepository
from app.schemas.finding import FindingCreate, FindingOut, FindingUpdate
from app.services.audit_service import AuditService


class FindingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FindingRepository(db)
        self.cves = CveRepository(db)
        self.audit = AuditService(db)

    def _cve_map(self, cve_record_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not cve_record_ids:
            return {}
        rows = self.db.execute(
            select(CveRecord.id, CveRecord.cve_id).where(CveRecord.id.in_(cve_record_ids))
        ).all()
        return {r[0]: r[1] for r in rows}

    def to_out(
        self, f: VulnerabilityFinding, cve_map: dict[uuid.UUID, str] | None = None
    ) -> FindingOut:
        cmap = cve_map or self._cve_map({f.cve_record_id})
        return FindingOut(
            id=str(f.id),
            asset_id=str(f.asset_id),
            cve_record_id=str(f.cve_record_id),
            cve_id=cmap.get(f.cve_record_id),
            status=f.status,
            discovered_at=f.discovered_at,
            remediated_at=f.remediated_at,
            due_at=f.due_at,
            assigned_to_user_id=str(f.assigned_to_user_id) if f.assigned_to_user_id else None,
            internal_priority_score=f.internal_priority_score,
            notes=f.notes,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )

    def list_findings(
        self,
        *,
        limit: int,
        offset: int,
        status: str | None,
        asset_id: uuid.UUID | None,
        cve_id_contains: str | None,
        search: str | None,
    ) -> tuple[list[FindingOut], int]:
        rows, total = self.repo.list_findings(
            limit=limit,
            offset=offset,
            status=status,
            asset_id=asset_id,
            cve_id_contains=cve_id_contains,
            search=search,
        )
        ids = {f.cve_record_id for f in rows}
        cmap = self._cve_map(ids)
        return [self.to_out(f, cmap) for f in rows], total

    def get(self, finding_id: uuid.UUID) -> FindingOut | None:
        f = self.repo.get_by_id(finding_id)
        if not f:
            return None
        return self.to_out(f)

    def create(self, data: FindingCreate, *, actor_id: uuid.UUID | None) -> FindingOut:
        asset_id = uuid.UUID(data.asset_id)
        cve_record_id: uuid.UUID | None = None
        if data.cve_record_id:
            cve_record_id = uuid.UUID(data.cve_record_id)
        elif data.cve_id:
            cve = self.cves.get_by_cve_id(data.cve_id)
            if not cve:
                raise ValueError("CVE not found")
            cve_record_id = cve.id
        else:
            raise ValueError("cve_record_id or cve_id required")

        if self.db.get(Asset, asset_id) is None:
            raise ValueError("Asset not found")

        existing = self.db.execute(
            select(VulnerabilityFinding).where(
                VulnerabilityFinding.asset_id == asset_id,
                VulnerabilityFinding.cve_record_id == cve_record_id,
            )
        ).scalar_one_or_none()
        if existing:
            raise ValueError("Finding already exists for this asset and CVE")

        discovered = data.discovered_at or datetime.now(timezone.utc)
        assigned = (
            uuid.UUID(data.assigned_to_user_id.strip())
            if data.assigned_to_user_id and data.assigned_to_user_id.strip()
            else None
        )

        row = VulnerabilityFinding(
            asset_id=asset_id,
            cve_record_id=cve_record_id,
            status=data.status,
            discovered_at=discovered,
            due_at=data.due_at,
            notes=data.notes,
            assigned_to_user_id=assigned,
        )
        self.repo.create(row)
        self.audit.record(
            actor_user_id=actor_id,
            action="finding.create",
            resource_type="vulnerability_finding",
            resource_id=str(row.id),
            payload={"asset_id": str(asset_id), "cve_record_id": str(cve_record_id)},
        )
        self.db.commit()
        self.db.refresh(row)
        return self.to_out(row)

    def update(
        self, finding_id: uuid.UUID, data: FindingUpdate, *, actor_id: uuid.UUID | None
    ) -> FindingOut | None:
        f = self.repo.get_by_id(finding_id)
        if not f:
            return None
        before = {"status": f.status}
        patch = data.model_dump(exclude_unset=True)
        if "status" in patch and patch["status"] is not None:
            f.status = patch["status"]
        if "due_at" in patch:
            f.due_at = patch["due_at"]
        if "remediated_at" in patch:
            f.remediated_at = patch["remediated_at"]
        if "notes" in patch:
            f.notes = patch["notes"]
        if "assigned_to_user_id" in patch:
            raw = patch["assigned_to_user_id"]
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                f.assigned_to_user_id = None
            else:
                f.assigned_to_user_id = uuid.UUID(str(raw).strip())
        if "internal_priority_score" in patch and patch["internal_priority_score"] is not None:
            f.internal_priority_score = patch["internal_priority_score"]
        self.db.flush()
        self.audit.record(
            actor_user_id=actor_id,
            action="finding.update",
            resource_type="vulnerability_finding",
            resource_id=str(f.id),
            payload={"before": before, "after": {"status": f.status}},
        )
        self.db.commit()
        self.db.refresh(f)
        return self.to_out(f)

    def delete(self, finding_id: uuid.UUID, *, actor_id: uuid.UUID | None) -> bool:
        f = self.repo.get_by_id(finding_id)
        if not f:
            return False
        fid = str(f.id)
        self.repo.delete(f)
        self.audit.record(
            actor_user_id=actor_id,
            action="finding.delete",
            resource_type="vulnerability_finding",
            resource_id=fid,
        )
        self.db.commit()
        return True
