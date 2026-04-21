"""Policy and compliance models.

Provides PolicyRule, PolicyViolation, and related models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.common import Base, TimestampMixin, UUIDMixin
from app.constants import PolicyRuleType, ComplianceStatus, SeverityLevel


class PolicyRule(Base, UUIDMixin, TimestampMixin):
    """Policy rule definition for compliance and workflow enforcement."""
    
    __tablename__ = "policy_rules"
    __table_args__ = (
        Index("ix_policy_rules_tenant_enabled", "tenant_id", "is_enabled"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Rule definition
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(
        String(50),
        default=PolicyRuleType.SEVERITY_THRESHOLD.value,
        nullable=False,
    )
    
    # Rule configuration
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    
    # Conditions
    severity_threshold: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    asset_criticality: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    
    # Status
    is_enabled: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )
    priority: Mapped[int] = mapped_column(default=100, nullable=False)
    
    # Enforcement
    auto_assign_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    required_approver_role: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    
    # Relationships
    violations: Mapped[list["PolicyViolation"]] = relationship(back_populates="rule")


class PolicyViolation(Base, UUIDMixin, TimestampMixin):
    """Records of policy violations."""
    
    __tablename__ = "policy_violations"
    __table_args__ = (
        Index("ix_violations_tenant_status", "tenant_id", "status"),
        Index("ix_violations_finding", "finding_id"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("policy_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=True,
    )
    
    # Violation details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[int] = mapped_column(
        default=SeverityLevel.MEDIUM, nullable=False
    )
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        default=ComplianceStatus.NON_COMPLIANT.value,
        nullable=False,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    rule: Mapped["PolicyRule"] = relationship(back_populates="violations")


class ComplianceFramework(Base, UUIDMixin, TimestampMixin):
    """Compliance framework definitions (SOC2, ISO27001, etc.)."""
    
    __tablename__ = "compliance_frameworks"
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Framework settings
    requirements: Mapped[Optional[list[dict]]] = mapped_column(JSONB, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(
        default=True, server_default="true", nullable=False
    )


class ComplianceMapping(Base, UUIDMixin, TimestampMixin):
    """Mapping between findings and compliance requirements."""
    
    __tablename__ = "compliance_mappings"
    __table_args__ = (
        Index("ix_compliance_mapping_finding", "finding_id"),
        Index("ix_compliance_mapping_framework", "framework_id"),
    )
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    
    finding_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
    )
    framework_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("compliance_frameworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    requirement_id: Mapped[str] = mapped_column(String(100), nullable=False)
    control_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default=ComplianceStatus.PENDING.value,
        nullable=False,
    )
    
    # Ensure unique mapping per finding/framework/requirement
    __table_args__ = (
        Index("ix_compliance_mapping_finding", "finding_id"),
        Index("ix_compliance_mapping_framework", "framework_id"),
        Index(
            "ix_compliance_mapping_unique",
            "finding_id",
            "framework_id",
            "requirement_id",
            unique=True,
        ),
    )
