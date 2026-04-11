from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
FindingStatus = Literal[
    "OPEN",
    "IN_PROGRESS",
    "RISK_ACCEPTED",
    "REMEDIATED",
    "FALSE_POSITIVE",
]


class CveCsvRow(BaseModel):
    """Row shape for `database/seeds/cve_records.csv` (includes surrogate OLTP id)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: UUID
    cve_id: str = Field(..., min_length=8, max_length=32)
    title: Optional[str] = Field(default=None, max_length=512)
    severity: Severity
    cvss_base_score: Optional[Decimal] = Field(default=None, ge=0, le=10)
    epss_score: Optional[Decimal] = Field(default=None, ge=0, le=1)
    exploit_available: bool = False


class CveSeedRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    cve_id: str = Field(..., min_length=8, max_length=32)
    title: Optional[str] = Field(default=None, max_length=512)
    severity: Severity
    cvss_base_score: Optional[Decimal] = Field(default=None, ge=0, le=10)
    epss_score: Optional[Decimal] = Field(default=None, ge=0, le=1)
    exploit_available: bool = False


class AssetCsvRow(BaseModel):
    """Row shape for `database/seeds/assets.csv`."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: str = Field(..., min_length=1, max_length=64)
    hostname: Optional[str] = Field(default=None, max_length=253)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    business_unit_code: str = Field(..., min_length=1, max_length=64)
    team_name: Optional[str] = Field(default=None, max_length=200)
    criticality: int = Field(default=3, ge=1, le=5)
    owner_email: Optional[str] = Field(default=None, max_length=320)


class AssetSeedRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: UUID
    name: str = Field(..., min_length=1, max_length=200)
    asset_type: str = Field(..., min_length=1, max_length=64)
    hostname: Optional[str] = Field(default=None, max_length=253)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    business_unit_code: str = Field(..., min_length=1, max_length=64)
    team_name: Optional[str] = Field(default=None, max_length=200)
    criticality: int = Field(default=3, ge=1, le=5)
    owner_email: Optional[str] = Field(default=None, max_length=320)


class FindingCsvRow(BaseModel):
    """Row shape for `database/seeds/vulnerability_findings.csv`."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: UUID
    asset_id: UUID
    cve_id: str = Field(..., min_length=8, max_length=32)
    status: FindingStatus
    discovered_at: datetime
    due_at: Optional[datetime] = None
    assignee_email: Optional[str] = Field(default=None, max_length=320)

    @field_validator("discovered_at", "due_at", mode="before")
    @classmethod
    def parse_dt(cls, v):
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            if not str(v).strip():
                return None
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        raise TypeError("invalid datetime")


class FindingSeedRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id: UUID
    asset_id: UUID
    cve_id: str = Field(..., min_length=8, max_length=32)
    status: FindingStatus
    discovered_at: datetime
    due_at: Optional[datetime] = None
    assignee_email: Optional[str] = Field(default=None, max_length=320)

    @field_validator("discovered_at", "due_at", mode="before")
    @classmethod
    def parse_dt(cls, v):
        if v is None or isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        raise TypeError("invalid datetime")
