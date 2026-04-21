from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.oltp import OrganizationInvitation


class InvitationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, invitation: OrganizationInvitation) -> OrganizationInvitation:
        self.db.add(invitation)
        self.db.flush()
        self.db.refresh(invitation)
        return invitation

    def get_valid_by_hash(self, token_hash: str) -> OrganizationInvitation | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(OrganizationInvitation)
            .where(OrganizationInvitation.token_hash == token_hash)
            .where(OrganizationInvitation.accepted_at.is_(None))
            .where(OrganizationInvitation.expires_at > now)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def mark_accepted(self, invitation_id: uuid.UUID) -> None:
        invitation = self.db.get(OrganizationInvitation, invitation_id)
        if invitation is None:
            return
        invitation.accepted_at = datetime.now(timezone.utc)
        self.db.flush()

    def find_active_by_email(self, tenant_id: uuid.UUID, email: str) -> OrganizationInvitation | None:
        now = datetime.now(timezone.utc)
        normalized = email.strip().lower()
        stmt = (
            select(OrganizationInvitation)
            .where(OrganizationInvitation.tenant_id == tenant_id)
            .where(func.lower(OrganizationInvitation.email) == normalized)
            .where(OrganizationInvitation.accepted_at.is_(None))
            .where(OrganizationInvitation.expires_at > now)
            .order_by(OrganizationInvitation.created_at.desc())
        )
        return self.db.execute(stmt).scalar_one_or_none()
