"""Common base model and utilities for all database models.

Provides:
- Base class with common columns (id, created_at, updated_at)
- UUID type helpers
- Tenant mixin for multi-tenant models
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.
    
    Provides:
    - Automatic table name generation
    - JSON serialization support
    """
    
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (CamelCase -> snake_case)."""
        name = cls.__name__
        # Convert CamelCase to snake_case
        result = []
        for i, char in enumerate(name):
            if char.isupper() and i > 0 and name[i-1].islower():
                result.append("_")
            result.append(char.lower())
        return "".join(result) + "s"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def __repr__(self) -> str:
        """String representation."""
        columns = [f"{k}={v}" for k, v in self.to_dict().items() if k == "id"]
        return f"<{self.__class__.__name__}({', '.join(columns)})>"


class TimestampMixin:
    """Mixin providing created_at and updated_at timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class TenantMixin:
    """Mixin for multi-tenant models requiring tenant_id."""
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    
    @declared_attr.directive
    def __table_args__(cls):
        """Add tenant index to table args."""
        return (
            Index(f"ix_{cls.__tablename__}_tenant", "tenant_id"),
        )


class SoftDeleteMixin:
    """Mixin providing soft delete functionality."""
    
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        server_default="false",
        nullable=False,
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    
    def soft_delete(self, deleted_by: Optional[uuid.UUID] = None) -> None:
        """Soft delete this record."""
        self.is_deleted = True
        self.deleted_at = datetime.now(datetime.timezone.utc)
        self.deleted_by = deleted_by
    
    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None


class UUIDMixin:
    """Mixin providing UUID primary key."""
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
