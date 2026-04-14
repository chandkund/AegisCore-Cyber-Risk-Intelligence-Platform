from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, row: RefreshToken) -> RefreshToken:
        self.db.add(row)
        self.db.flush()
        self.db.refresh(row)
        return row

    def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke(self, token_id: uuid.UUID) -> None:
        row = self.db.get(RefreshToken, token_id)
        if row and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            self.db.flush()

    def revoke_by_hash(self, token_hash: str) -> None:
        row = self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none()
        if row and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            self.db.flush()
