"""Schemas for data upload endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ValidationError(BaseModel):
    """Single validation error for a row."""
    row_number: int
    field: str | None = None
    message: str
    raw_data: dict[str, Any] | None = None


class ImportSummary(BaseModel):
    """Summary of an import operation."""
    total_rows: int
    inserted: int
    updated: int
    failed: int
    skipped: int
    errors: list[ValidationError]
    processing_time_ms: int
    imported_at: datetime


class AssetUploadResponse(BaseModel):
    """Response for asset CSV upload."""
    success: bool
    message: str
    summary: ImportSummary
    import_id: str | None = None


class VulnerabilityUploadResponse(BaseModel):
    """Response for vulnerability CSV upload."""
    success: bool
    message: str
    summary: ImportSummary
    import_id: str | None = None


class MappingUploadResponse(BaseModel):
    """Response for asset-vulnerability mapping CSV upload."""
    success: bool
    message: str
    summary: ImportSummary
    import_id: str | None = None


class BulkImportStatus(BaseModel):
    """Status of a bulk import job."""
    import_id: str
    status: str  # "pending", "processing", "completed", "failed"
    entity_type: str  # "assets", "vulnerabilities", "mappings"
    progress_percent: int
    summary: ImportSummary | None = None
    created_at: datetime
    completed_at: datetime | None = None
    created_by: str


@dataclass
class ParsedAsset:
    """Validated asset data from CSV."""
    name: str
    asset_type: str
    hostname: str | None
    ip_address: str | None
    business_unit_code: str
    team_name: str | None
    location_name: str | None
    criticality: int
    owner_email: str | None
    is_active: bool = True


@dataclass
class ParsedVulnerability:
    """Validated vulnerability data from CSV."""
    cve_id: str
    asset_identifier: str  # hostname or IP for matching
    status: str
    discovered_at: datetime | None
    due_at: datetime | None
    notes: str | None
    assigned_to_email: str | None


@dataclass
class ParsedMapping:
    """Validated asset-vulnerability mapping from CSV."""
    asset_identifier: str  # hostname or IP
    cve_id: str
    discovered_date: str | None
    status: str = "OPEN"
