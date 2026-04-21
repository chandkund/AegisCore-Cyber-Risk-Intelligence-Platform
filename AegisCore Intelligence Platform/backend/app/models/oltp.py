from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base
from app.core.security import hash_password, verify_password

# Use database-agnostic JSON type (works with PostgreSQL JSONB and SQLite)
JSONType = JSON


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512))


class Organization(Base):
    """Company/tenant registry with lifecycle management.

    Represents a company in the SaaS platform. Contains both the business
    identity (name, code, slug) and lifecycle state (status, approval).
    """

    __tablename__ = "organizations"

    # Primary identification
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    slug: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )

    # Lifecycle status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    status: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, server_default="pending"
    )  # pending, active, suspended

    # Approval workflow
    approval_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="approved"
    )  # pending, approved, rejected
    approval_notes: Mapped[Optional[str]] = mapped_column(String(500))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Primary admin (nullable to avoid circular dependency during creation)
    primary_admin_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )


class User(Base):
    """User accounts with company membership.

    Supports both company users (with tenant_id) and platform owners
    (with nullable tenant_id for cross-company access).
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("ix_users_tenant_email", "tenant_id", "email"),
        Index("ix_users_email", "email"),
    )

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Company membership (nullable for platform_owner users)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    # Identity
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Authentication
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    require_password_change: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )  # Force password change on first login (e.g., for auto-generated passwords)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")

    # Legacy field aliases used by older tests/modules.
    company_id = synonym("tenant_id")
    name = synonym("full_name")

    def __init__(self, **kwargs):
        self._legacy_is_company_admin = bool(kwargs.pop("is_company_admin", False))
        self._legacy_is_platform_owner = bool(kwargs.pop("is_platform_owner", False))
        if "company_id" in kwargs and "tenant_id" not in kwargs:
            kwargs["tenant_id"] = kwargs.pop("company_id")
        if "name" in kwargs and "full_name" not in kwargs:
            kwargs["full_name"] = kwargs.pop("name")
        super().__init__(**kwargs)

    @property
    def is_platform_owner(self) -> bool:
        role_names = {ur.role.name for ur in self.roles if ur.role is not None}
        return "platform_owner" in role_names or getattr(self, "_legacy_is_platform_owner", False)

    @property
    def is_company_admin(self) -> bool:
        role_names = {ur.role.name for ur in self.roles if ur.role is not None}
        return "admin" in role_names or getattr(self, "_legacy_is_company_admin", False)

    def set_password(self, plain_password: str) -> None:
        self.hashed_password = hash_password(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return verify_password(plain_password, self.hashed_password)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship()


class BusinessUnit(Base):
    __tablename__ = "business_units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_business_units_tenant_code"),
        Index("ix_business_units_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_business_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL")
    )


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_teams_tenant_name"),
        Index("ix_teams_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=False
    )


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_locations_tenant_name"),
        Index("ix_locations_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(120))
    country_code: Mapped[Optional[str]] = mapped_column(String(2))


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_business_unit_team", "business_unit_id", "team_id"),
        Index("ix_assets_criticality", "criticality"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(253))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL")
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL")
    )
    criticality: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="3")
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", index=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(320))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    findings: Mapped[list["VulnerabilityFinding"]] = relationship(back_populates="asset")


class AssetAttribute(Base):
    __tablename__ = "asset_attributes"
    __table_args__ = (UniqueConstraint("asset_id", "key", name="uq_asset_attributes_asset_key"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class AssetDependency(Base):
    __tablename__ = "asset_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_asset_id",
            "target_asset_id",
            name="uq_asset_dependencies_tenant_source_target",
        ),
        Index("ix_asset_dependencies_tenant_source", "tenant_id", "source_asset_id"),
        Index("ix_asset_dependencies_tenant_target", "tenant_id", "target_asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    dependency_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default="network")
    trust_level: Mapped[str] = mapped_column(String(32), nullable=False, server_default="medium")
    lateral_movement_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CveRecord(Base):
    __tablename__ = "cve_records"
    __table_args__ = (Index("ix_cve_records_severity_cvss", "severity", "cvss_base_score"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cve_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(512))
    description: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cvss_base_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    cvss_vector: Mapped[Optional[str]] = mapped_column(String(128))
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    epss_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 5))
    exploit_available: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    findings: Mapped[list["VulnerabilityFinding"]] = relationship(back_populates="cve_record")


class VulnerabilityFinding(Base):
    __tablename__ = "vulnerability_findings"
    __table_args__ = (
        UniqueConstraint("asset_id", "cve_record_id", name="uq_findings_asset_cve"),
        Index("ix_findings_status_due", "status", "due_at"),
        Index("ix_findings_discovered", "discovered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    cve_record_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cve_records.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remediated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    internal_priority_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True, index=True)
    risk_factors: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    risk_calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="findings")
    cve_record: Mapped["CveRecord"] = relationship(back_populates="findings")


class RemediationEvent(Base):
    __tablename__ = "remediation_events"
    __table_args__ = (Index("ix_remediation_events_finding", "finding_id", "occurred_at"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vulnerability_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(32))
    new_status: Mapped[Optional[str]] = mapped_column(String(32))
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details: Mapped[Optional[dict]] = mapped_column(JSONType)


class SlaPolicy(Base):
    __tablename__ = "sla_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_sla_policies_tenant_name"),
        Index("ix_sla_policies_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    max_days_to_remediate: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditLog(Base):
    """Comprehensive audit trail for all platform actions.

    Records who (actor) performed what (action) on which resource (target),
    including the actor's role at time of action for compliance.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
        Index("ix_audit_log_occurred", "occurred_at"),
        Index("ix_audit_log_tenant", "tenant_id"),
        Index("ix_audit_log_actor", "actor_user_id"),
        Index("ix_audit_log_company_time", "tenant_id", "occurred_at"),
    )

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Target (what was affected) - uses resource_type/resource_id pattern
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), index=True
    )
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)  # target_type
    resource_id: Mapped[Optional[str]] = mapped_column(String(64))  # target_id

    # Actor (who performed the action)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True, index=True)
    actor_role: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )  # Denormalized role at time of action

    # Action details
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONType)  # metadata

    # Timestamp
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at = synonym("occurred_at")


class EtlWatermark(Base):
    __tablename__ = "etl_watermarks"

    pipeline_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    high_watermark: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user", "user_id", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_org_invites_token_hash"),
        Index("ix_org_invites_tenant_email", "tenant_id", "email"),
        Index("ix_org_invites_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RemediationTicket(Base):
    __tablename__ = "remediation_tickets"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "provider",
            "external_ticket_id",
            name="uq_remediation_tickets_provider_external_per_tenant",
        ),
        Index("ix_remediation_tickets_finding", "finding_id"),
        Index("ix_remediation_tickets_provider_status", "provider", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("vulnerability_findings.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_ticket_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="OPEN")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONType)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    __table_args__ = (
        Index("ix_policy_rules_tenant_enabled", "tenant_id", "is_enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    conditions: Mapped[dict] = mapped_column(JSONType, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, server_default="flag")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, server_default="MEDIUM")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PrioritizationFeedback(Base):
    __tablename__ = "prioritization_feedback"
    __table_args__ = (
        Index("ix_prioritization_feedback_finding", "finding_id"),
        Index("ix_prioritization_feedback_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("vulnerability_findings.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(2000))
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BackgroundJob(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        Index("ix_background_jobs_tenant_status", "tenant_id", "status"),
        Index("ix_background_jobs_kind_created", "job_kind", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="QUEUED")
    payload: Mapped[Optional[dict]] = mapped_column(JSONType)
    result: Mapped[Optional[dict]] = mapped_column(JSONType)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EmailVerificationOTP(Base):
    """Email verification OTP with brute force protection."""
    __tablename__ = "email_verification_otps"
    __table_args__ = (
        Index("ix_email_otps_user_id", "user_id"),
        Index("ix_email_otps_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 6-digit OTP stored as hashed value (never store raw OTP)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Track attempts for brute force protection
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UploadImport(Base):
    """Tracks data import uploads (assets, vulnerabilities, mappings).

    This table provides:
    - Audit trail for data imports
    - Import history per tenant
    - Processing status and results
    - Error tracking for failed imports

    Platform Owner can view all uploads (governance).
    Tenant Admin can view own tenant uploads.
    """
    __tablename__ = "upload_imports"
    __table_args__ = (
        Index("ix_upload_imports_tenant_created", "tenant_id", "created_at"),
        Index("ix_upload_imports_tenant_type", "tenant_id", "upload_type"),
        Index("ix_upload_imports_status", "status"),
        Index("ix_upload_imports_uploader", "uploaded_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Upload classification
    upload_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # assets_import, vulnerabilities_import, mappings_import

    # File metadata (original upload)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))

    # Processing status
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="processing")
    # processing, completed, failed, partial

    # Import results (stored as JSON for flexibility)
    summary: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # {
    #   "total_rows": 100,
    #   "inserted": 80,
    #   "updated": 15,
    #   "failed": 5,
    #   "skipped": 0,
    #   "errors": [{"row": 10, "field": "name", "message": "..."}]
    # }

    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class UploadFile(Base):
    """Tracks file uploads (documents, reports, scan results).

    For generic file storage (not data imports).
    Files are stored on disk at: {UPLOAD_DIR}/{tenant_id}/{storage_path}

    Platform Owner can view all uploads (governance).
    Tenant Admin can view own tenant uploads.
    """
    __tablename__ = "upload_files"
    __table_args__ = (
        Index("ix_upload_files_tenant_created", "tenant_id", "created_at"),
        Index("ix_upload_files_tenant_type", "tenant_id", "upload_type"),
        Index("ix_upload_files_uploader", "uploaded_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Upload classification
    upload_type: Mapped[str] = mapped_column(String(64), nullable=False, server_default="document")
    # document, scan_report, evidence, supporting_document, etc.

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    # Relative path: {tenant_id}/{file_id}{ext}

    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))

    # Optional description
    description: Mapped[Optional[str]] = mapped_column(String(1000))

    # Security fields
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hash prefix of file content"
    )
    scan_status: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, server_default="pending",
        comment="Virus scan result: clean, infected, error, disabled, pending"
    )
    scan_threat: Mapped[Optional[str]] = mapped_column(
        String(256), nullable=True, comment="Threat name if infected"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# Backward-compatible aliases for legacy imports in older tests/modules.
Company = Organization
Finding = VulnerabilityFinding
Vulnerability = VulnerabilityFinding
