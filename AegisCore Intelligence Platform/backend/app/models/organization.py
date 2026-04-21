"""Organization and tenant-related models.

Provides Organization, BusinessUnit, Team models.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class Organization(Base, UUIDMixin, TimestampMixin):
    """Organization/tenant model.
    
    Represents a customer organization with multi-tenant isolation.
    """
    
    __tablename__ = "organizations"
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Settings
    settings: Mapped[Optional[dict]] = mapped_column(default=dict)
    
    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organization",
        foreign_keys="User.tenant_id",
    )
    business_units: Mapped[list["BusinessUnit"]] = relationship(
        back_populates="organization"
    )
    teams: Mapped[list["Team"]] = relationship(back_populates="organization")


class BusinessUnit(Base, UUIDMixin):
    """Business unit within an organization."""
    
    __tablename__ = "business_units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_business_units_tenant_code"),
        Index("ix_business_units_tenant", "tenant_id"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    parent_business_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("business_units.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Relationships
    organization: Mapped["Organization"] = relationship(
        back_populates="business_units"
    )
    parent: Mapped[Optional["BusinessUnit"]] = relationship(
        remote_side="BusinessUnit.id"
    )
    children: Mapped[list["BusinessUnit"]] = relationship(
        back_populates="parent"
    )


class Team(Base, UUIDMixin):
    """Team within an organization."""
    
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_teams_tenant_name"),
        Index("ix_teams_tenant", "tenant_id"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="teams")
