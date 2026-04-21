"""Repository for email verification operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.email_verification import EmailVerification


class EmailVerificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: uuid.UUID, code: str, expires_minutes: int = 15) -> EmailVerification:
        """Create a new verification code."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
        verification = EmailVerification(
            user_id=user_id,
            code=code,
            expires_at=expires_at,
        )
        self.db.add(verification)
        self.db.flush()
        self.db.refresh(verification)
        return verification

    def get_by_user_id(self, user_id: uuid.UUID) -> EmailVerification | None:
        """Get the most recent unverified code for a user."""
        stmt = (
            select(EmailVerification)
            .where(
                EmailVerification.user_id == user_id,
                EmailVerification.is_verified == False
            )
            .order_by(desc(EmailVerification.created_at))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> EmailVerification | None:
        """Get verification by code."""
        stmt = (
            select(EmailVerification)
            .where(EmailVerification.code == code)
            .order_by(desc(EmailVerification.created_at))
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def increment_attempts(self, verification: EmailVerification) -> None:
        """Increment attempt counter."""
        verification.attempts += 1
        self.db.flush()

    def mark_verified(self, verification: EmailVerification) -> None:
        """Mark verification as completed."""
        verification.is_verified = True
        verification.verified_at = datetime.now(timezone.utc)
        self.db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all pending verifications for a user."""
        stmt = select(EmailVerification).where(
            EmailVerification.user_id == user_id,
            EmailVerification.is_verified == False
        )
        verifications = self.db.execute(stmt).scalars().all()
        for v in verifications:
            v.is_verified = True  # Mark as used to prevent reuse
        self.db.flush()
