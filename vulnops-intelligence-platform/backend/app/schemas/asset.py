from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# JSON encoders for complex types
JSON_ENCODERS = {
    datetime: lambda v: v.isoformat() if v else None,
    Decimal: lambda v: str(v) if v is not None else None,
}


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    asset_type: str = Field(min_length=1, max_length=64)
    hostname: str | None = Field(default=None, max_length=253)
    ip_address: str | None = Field(default=None, max_length=45)
    business_unit_id: str
    team_id: str | None = None
    location_id: str | None = None
    criticality: int = Field(default=3, ge=1, le=5)
    owner_email: str | None = Field(default=None, max_length=320)
    is_active: bool = True


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    asset_type: str | None = Field(default=None, min_length=1, max_length=64)
    hostname: str | None = Field(default=None, max_length=253)
    ip_address: str | None = Field(default=None, max_length=45)
    business_unit_id: str | None = None
    team_id: str | None = None
    location_id: str | None = None
    criticality: int | None = Field(default=None, ge=1, le=5)
    owner_email: str | None = Field(default=None, max_length=320)
    is_active: bool | None = None


class AssetOut(BaseModel):
    model_config = {
        "from_attributes": True,
        "json_encoders": JSON_ENCODERS,
    }

    id: str
    name: str
    asset_type: str
    hostname: str | None
    ip_address: str | None
    business_unit_id: str
    team_id: str | None
    location_id: str | None
    criticality: int
    owner_email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
