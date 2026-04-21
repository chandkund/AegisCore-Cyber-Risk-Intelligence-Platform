"""Email verification model for OTP-based user verification."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmailVerification(Base):
    """Email verification codes for new user registration.
    
    Stores 6-digit OTP codes with expiry for email verification.
    """
    __tablename__ = "email_verifications"
    __table_args__ = (
        Index("ix_email_verifications_user_id", "user_id"),
        Index("ix_email_verifications_code", "code"),
        Index("ix_email_verifications_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    
    # 6-digit OTP code
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    
    # Expiration tracking
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Verification status
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Attempt tracking (prevent brute force)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    def is_expired(self) -> bool:
        """Check if verification code has expired."""
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at
    
    def can_attempt(self) -> bool:
        """Check if more attempts are allowed."""
        return self.attempts < self.max_attempts and not self.is_verified and not self.is_expired()
    
    def verify(self) -> bool:
        """Mark as verified if valid."""
        if self.is_expired() or self.is_verified:
            return False
        self.is_verified = True
        self.verified_at = datetime.now(timezone.utc)
        return True
