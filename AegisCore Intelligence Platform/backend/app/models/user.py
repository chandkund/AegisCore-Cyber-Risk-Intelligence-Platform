"""User and authentication models.

Provides User, Role, UserRole models with no circular dependencies.
Password handling is delegated to the service layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from app.models.common import Base, TimestampMixin, UUIDMixin
from app.constants import UserStatusEnum

if TYPE_CHECKING:
    # Avoid circular imports at runtime
    from app.models.organization import Organization


class Role(Base, UUIDMixin):
    """Role definition (platform_owner, admin, user, etc.)."""
    
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(back_populates="role")


class UserRole(Base):
    """Association table linking users to roles."""
    
    __tablename__ = "user_roles"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")


class User(Base, UUIDMixin, TimestampMixin):
    """User account model.
    
    Password handling is done via UserService, not in the model,
    eliminating circular dependencies with security utilities.
    """
    
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_tenant", "tenant_id"),
        Index("ix_users_email", "email"),
    )
    
    # Organization membership (nullable for platform_owner users)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    
    # Identity
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # Authentication (hashed password stored here, but hashing done elsewhere)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # MFA
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    mfa_backup_codes: Mapped[Optional[list[str]]] = mapped_column(
        default=None, nullable=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=UserStatusEnum.ACTIVE.value,
        server_default=UserStatusEnum.ACTIVE.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    require_password_change: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    
    # Security tracking
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="users"
    )
    
    # Legacy field aliases for backward compatibility
    @hybrid_property
    def company_id(self) -> Optional[uuid.UUID]:
        return self.tenant_id
    
    @hybrid_property
    def name(self) -> str:
        return self.full_name
    
    def __init__(self, **kwargs):
        # Handle legacy field names
        if "company_id" in kwargs and "tenant_id" not in kwargs:
            kwargs["tenant_id"] = kwargs.pop("company_id")
        if "name" in kwargs and "full_name" not in kwargs:
            kwargs["full_name"] = kwargs.pop("name")
        
        # Handle legacy role flags
        self._legacy_is_company_admin = bool(kwargs.pop("is_company_admin", False))
        self._legacy_is_platform_owner = bool(kwargs.pop("is_platform_owner", False))
        
        super().__init__(**kwargs)
    
    @property
    def is_platform_owner(self) -> bool:
        """Check if user has platform_owner role."""
        role_names = {ur.role.name for ur in self.roles if ur.role is not None}
        return "platform_owner" in role_names or getattr(
            self, "_legacy_is_platform_owner", False
        )
    
    @property
    def is_company_admin(self) -> bool:
        """Check if user has admin role."""
        role_names = {ur.role.name for ur in self.roles if ur.role is not None}
        return "admin" in role_names or getattr(
            self, "_legacy_is_company_admin", False
        )
    
    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return self.locked_until > datetime.now(datetime.timezone.utc)
    
    def record_login_attempt(self, success: bool) -> None:
        """Record a login attempt. Updates failed attempts and lock status."""
        from app.constants import MAX_FAILED_LOGIN_ATTEMPTS, LOCKOUT_DURATION_MINUTES
        
        if success:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.last_login_at = datetime.now(datetime.timezone.utc)
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                from datetime import timedelta
                self.locked_until = datetime.now(
                    datetime.timezone.utc
                ) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


class EmailVerificationOTP(Base, UUIDMixin, TimestampMixin):
    """Email verification one-time passwords."""
    
    __tablename__ = "email_verification_otps"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    otp_code: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    
    # Relationships
    user: Mapped["User"] = relationship("User")
