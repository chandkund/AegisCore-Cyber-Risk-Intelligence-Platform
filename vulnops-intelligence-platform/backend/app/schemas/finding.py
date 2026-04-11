from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class FindingBase(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    discovered_at: datetime
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    assigned_to_user_id: str | None = None


class FindingCreate(BaseModel):
    asset_id: str
    cve_record_id: str | None = None
    cve_id: str | None = Field(
        default=None,
        description="Alternative to cve_record_id — resolved against cve_records.cve_id",
        max_length=32,
    )
    status: str = Field(default="OPEN", max_length=32)
    discovered_at: datetime | None = None
    due_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    assigned_to_user_id: str | None = None


class FindingUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    due_at: datetime | None = None
    remediated_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=10_000)
    assigned_to_user_id: str | None = None
    internal_priority_score: Decimal | None = Field(default=None, ge=0, le=9999.9999)


class FindingOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    asset_id: str
    cve_record_id: str
    cve_id: str | None = None
    status: str
    discovered_at: datetime
    remediated_at: datetime | None
    due_at: datetime | None
    assigned_to_user_id: str | None
    internal_priority_score: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
