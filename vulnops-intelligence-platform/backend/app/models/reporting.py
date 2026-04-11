from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

REPORTING_SCHEMA = "reporting"


class DimDate(Base):
    __tablename__ = "dim_date"
    __table_args__ = {"schema": REPORTING_SCHEMA}

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    full_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    week_of_year: Mapped[int] = mapped_column(Integer, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)


class DimBusinessUnit(Base):
    __tablename__ = "dim_business_unit"
    __table_args__ = (
        UniqueConstraint("business_unit_id", name="uq_dim_bu_natural"),
        {"schema": REPORTING_SCHEMA},
    )

    bu_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)


class DimTeam(Base):
    __tablename__ = "dim_team"
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_dim_team_natural"),
        {"schema": REPORTING_SCHEMA},
    )

    team_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    bu_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_business_unit.bu_key"), nullable=False
    )


class DimAsset(Base):
    __tablename__ = "dim_asset"
    __table_args__ = (
        UniqueConstraint("asset_id", name="uq_dim_asset_natural"),
        Index("ix_dim_asset_bu", "bu_key"),
        {"schema": REPORTING_SCHEMA},
    )

    asset_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, nullable=False)
    bu_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_business_unit.bu_key"), nullable=False
    )
    team_key: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_team.team_key")
    )


class DimCve(Base):
    __tablename__ = "dim_cve"
    __table_args__ = (
        UniqueConstraint("cve_record_id", name="uq_dim_cve_natural"),
        {"schema": REPORTING_SCHEMA},
    )

    cve_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cve_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cve_id: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    cvss_base_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))


class DimAssigneeUser(Base):
    __tablename__ = "dim_assignee_user"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_dim_assignee_natural"),
        {"schema": REPORTING_SCHEMA},
    )

    user_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)


class DimSeverity(Base):
    __tablename__ = "dim_severity"
    __table_args__ = (
        UniqueConstraint("severity_code", name="uq_dim_severity_code"),
        {"schema": REPORTING_SCHEMA},
    )

    severity_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    severity_code: Mapped[str] = mapped_column(String(16), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)


class FactVulnerabilitySnapshot(Base):
    __tablename__ = "fact_vulnerability_snapshot"
    __table_args__ = (
        UniqueConstraint("snapshot_date", "finding_oltp_id", name="uq_fact_snapshot_finding_day"),
        Index("ix_fact_snapshot_date_bu", "snapshot_date", "bu_key"),
        Index("ix_fact_snapshot_status", "status"),
        {"schema": REPORTING_SCHEMA},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    date_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_date.date_key"), nullable=False
    )
    finding_oltp_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_asset.asset_key"), nullable=False
    )
    cve_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_cve.cve_key"), nullable=False
    )
    bu_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_business_unit.bu_key"), nullable=False
    )
    team_key: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_team.team_key")
    )
    assignee_user_key: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_assignee_user.user_key")
    )
    severity_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{REPORTING_SCHEMA}.dim_severity.severity_key"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    cvss_base_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 2))
    epss_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 5))
    days_open: Mapped[int] = mapped_column(Integer, nullable=False)
    is_overdue: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exploit_available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
