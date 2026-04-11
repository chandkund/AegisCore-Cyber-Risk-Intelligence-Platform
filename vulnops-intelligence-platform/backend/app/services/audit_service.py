from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.oltp import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        actor_user_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        row = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )
        self.db.add(row)
        self.db.flush()
