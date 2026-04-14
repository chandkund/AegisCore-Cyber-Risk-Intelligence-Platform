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
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512))


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship(back_populates="roles")
    role: Mapped["Role"] = relationship()


class BusinessUnit(Base):
    __tablename__ = "business_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    parent_business_unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL")
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=False
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(120))
    country_code: Mapped[Optional[str]] = mapped_column(String(2))


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_business_unit_team", "business_unit_id", "team_id"),
        Index("ix_assets_criticality", "criticality"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(253))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    business_unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL")
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL")
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    cve_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cve_records.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    remediated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    internal_priority_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    risk_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True, index=True)
    risk_factors: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vulnerability_findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    old_status: Mapped[Optional[str]] = mapped_column(String(32))
    new_status: Mapped[Optional[str]] = mapped_column(String(32))
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details: Mapped[Optional[dict]] = mapped_column(JSONB)


class SlaPolicy(Base):
    __tablename__ = "sla_policies"
    __table_args__ = (UniqueConstraint("name", name="uq_sla_policies_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    max_days_to_remediate: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
        Index("ix_audit_log_occurred", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64))
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)


class EtlWatermark(Base):
    __tablename__ = "etl_watermarks"

    pipeline_name: Mapped[str] = mapped_column(String(120), primary_key=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    high_watermark: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user", "user_id", "expires_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vulnerability_findings.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_ticket_id: Mapped[str] = mapped_column(String(128), nullable=False)
    external_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="OPEN")
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vulnerability_findings.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(2000))
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    job_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="QUEUED")
    payload: Mapped[Optional[dict]] = mapped_column(JSONB)
    result: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
