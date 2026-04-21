"""Security and audit-related models.

Provides AuditLog, SecurityEvent, and related models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base, TimestampMixin, UUIDMixin
from app.constants import AuditAction, SeverityLevel


class AuditLog(Base, UUIDMixin):
    """Comprehensive audit log for security and compliance.
    
    Tracks all significant actions with full context for forensics.
    """
    
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_actor", "actor_user_id"),
    )
    
    # Actor information
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Action details
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Tenant context
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )
    
    # Request context
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    request_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Additional data
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[actor_user_id])


class SecurityEvent(Base, UUIDMixin):
    """Security events requiring attention (failed logins, anomalies, etc.).
    
    Separate from audit log for security monitoring and alerting.
    """
    
    __tablename__ = "security_events"
    __table_args__ = (
        Index("ix_security_events_tenant_severity", "tenant_id", "severity"),
        Index("ix_security_events_created", "created_at"),
    )
    
    # Event classification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[int] = mapped_column(
        Integer,
        default=SeverityLevel.MEDIUM,
        nullable=False,
    )
    
    # Context
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    
    # Event details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Resolution
    is_resolved: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Metadata
    metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PasswordResetToken(Base, UUIDMixin):
    """Password reset tokens."""
    
    __tablename__ = "password_reset_tokens"
    __table_args__ = (
        Index("ix_password_reset_user", "user_id"),
        Index("ix_password_reset_expires", "expires_at"),
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
