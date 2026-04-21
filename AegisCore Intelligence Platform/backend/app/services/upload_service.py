"""Service for handling tenant-aware CSV data uploads.

This service processes CSV uploads for assets, vulnerabilities, and mappings
with strict tenant validation and isolation.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.oltp import (
    Asset,
    BusinessUnit,
    CveRecord,
    Location,
    Organization,
    Team,
    UploadImport,
    User,
    VulnerabilityFinding,
)
from app.schemas.upload import (
    ImportSummary,
    ParsedAsset,
    ParsedMapping,
    ParsedVulnerability,
    ValidationError,
)
from app.services.audit_service import AuditService

if TYPE_CHECKING:
    from app.core.tenant import TenantContext


class UploadValidationError(Exception):
    """Raised when CSV validation fails."""
    pass


class UploadService:
    """Handle CSV uploads with tenant-aware data insertion."""

    def __init__(self, db: Session, tenant_context: "TenantContext"):
        self.db = db
        self.tenant_id = tenant_context.tenant_id
        self.tenant_context = tenant_context
        self.audit = AuditService(db)
        self._cache: dict[str, Any] = {}  # Cache for lookups

    # =========================================================================
    # Asset Upload
    # =========================================================================

    def upload_assets_csv(
        self,
        file_content: bytes,
        actor_user_id: uuid.UUID | None = None,
    ) -> ImportSummary:
        """Process asset CSV upload with tenant-aware insertion.
        
        Expected CSV columns:
        - name (required)
        - asset_type (required)
        - hostname (optional)
        - ip_address (optional)
        - business_unit_code (required)
        - team_name (optional)
        - location_name (optional)
        - criticality (optional, default 3)
        - owner_email (optional)
        """
        start_time = datetime.now(timezone.utc)
        errors: list[ValidationError] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        row_count = 0

        try:
            text = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
        except UnicodeDecodeError as e:
            raise UploadValidationError("File must be UTF-8 encoded") from e
        except Exception as e:
            raise UploadValidationError(f"Invalid CSV format: {e}") from e

        if not reader.fieldnames:
            raise UploadValidationError("CSV has no headers")

        required_cols = {"name", "asset_type", "business_unit_code"}
        normalized_headers = {f.strip().lower() for f in reader.fieldnames if f}
        if not required_cols <= normalized_headers:
            raise UploadValidationError(
                "CSV must include columns: name, asset_type, business_unit_code"
            )

        # Pre-load tenant data for validation
        self._preload_tenant_cache()

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
            row_count += 1
            
            try:
                parsed = self._parse_asset_row(row, row_num, errors)
                if parsed is None:
                    failed += 1
                    continue

                # Check if asset exists (by hostname or IP in this tenant)
                existing = self._find_existing_asset(parsed)
                
                if existing:
                    # Update existing asset
                    self._update_asset_from_parsed(existing, parsed)
                    updated += 1
                else:
                    # Create new asset
                    self._create_asset_from_parsed(parsed)
                    inserted += 1

            except Exception as e:
                errors.append(ValidationError(
                    row_number=row_num,
                    message=f"Unexpected error: {str(e)}",
                    raw_data=row,
                ))
                failed += 1

        self.db.commit()

        # Record audit log
        if actor_user_id and (inserted + updated) > 0:
            self.audit.record(
                actor_user_id=actor_user_id,
                action="upload.assets",
                resource_type="import",
                resource_id=str(uuid.uuid4()),
                payload={
                    "inserted": inserted,
                    "updated": updated,
                    "failed": failed,
                    "rows_processed": row_count,
                },
            )
            self.db.commit()

        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        return ImportSummary(
            total_rows=row_count,
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            errors=errors[:100],  # Limit errors returned
            processing_time_ms=processing_time,
            imported_at=datetime.now(timezone.utc),
        )

    def _parse_asset_row(
        self,
        row: dict[str, str],
        row_num: int,
        errors: list[ValidationError],
    ) -> ParsedAsset | None:
        """Parse and validate a single asset row."""
        # Required fields
        name = row.get("name", "").strip()
        if not name:
            errors.append(ValidationError(
                row_number=row_num,
                field="name",
                message="Asset name is required",
                raw_data=row,
            ))
            return None

        asset_type = row.get("asset_type", "").strip()
        if not asset_type:
            errors.append(ValidationError(
                row_number=row_num,
                field="asset_type",
                message="Asset type is required",
                raw_data=row,
            ))
            return None

        bu_code = row.get("business_unit_code", "").strip()
        if not bu_code:
            errors.append(ValidationError(
                row_number=row_num,
                field="business_unit_code",
                message="Business unit code is required",
                raw_data=row,
            ))
            return None

        # Validate business unit exists in tenant
        if bu_code not in self._cache.get("business_units", {}):
            errors.append(ValidationError(
                row_number=row_num,
                field="business_unit_code",
                message=f"Business unit '{bu_code}' not found in this company",
                raw_data=row,
            ))
            return None

        # Optional fields with validation
        hostname = row.get("hostname", "").strip() or None
        ip_address = row.get("ip_address", "").strip() or None

        if ip_address and not self._is_valid_ip(ip_address):
            errors.append(ValidationError(
                row_number=row_num,
                field="ip_address",
                message=f"Invalid IP address: {ip_address}",
                raw_data=row,
            ))
            return None

        # Criticality (1-5, default 3)
        criticality_str = row.get("criticality", "3").strip()
        try:
            criticality = int(criticality_str)
            if not 1 <= criticality <= 5:
                raise ValueError()
        except ValueError:
            errors.append(ValidationError(
                row_number=row_num,
                field="criticality",
                message=f"Criticality must be 1-5, got: {criticality_str}",
                raw_data=row,
            ))
            return None

        owner_email = row.get("owner_email", "").strip() or None
        if owner_email and not self._is_valid_email(owner_email):
            errors.append(ValidationError(
                row_number=row_num,
                field="owner_email",
                message=f"Invalid email: {owner_email}",
                raw_data=row,
            ))
            return None

        return ParsedAsset(
            name=name,
            asset_type=asset_type,
            hostname=hostname,
            ip_address=ip_address,
            business_unit_code=bu_code,
            team_name=row.get("team_name", "").strip() or None,
            location_name=row.get("location_name", "").strip() or None,
            criticality=criticality,
            owner_email=owner_email,
            is_active=True,
        )

    def _preload_tenant_cache(self) -> None:
        """Pre-load tenant data for validation during upload."""
        # Business units
        bu_stmt = select(BusinessUnit).where(
            BusinessUnit.tenant_id == self.tenant_id
        )
        business_units = {
            bu.code: bu for bu in self.db.execute(bu_stmt).scalars().all()
        }

        # Teams
        team_stmt = select(Team).where(Team.tenant_id == self.tenant_id)
        teams = {team.name: team for team in self.db.execute(team_stmt).scalars().all()}

        # Locations
        loc_stmt = select(Location).where(Location.tenant_id == self.tenant_id)
        locations = {loc.name: loc for loc in self.db.execute(loc_stmt).scalars().all()}

        # Users (for owner email validation)
        user_stmt = select(User).where(
            User.tenant_id == self.tenant_id,
            User.is_active == True,
        )
        users = {user.email: user for user in self.db.execute(user_stmt).scalars().all()}

        self._cache = {
            "business_units": business_units,
            "teams": teams,
            "locations": locations,
            "users": users,
        }

    def _find_existing_asset(self, parsed: ParsedAsset) -> Asset | None:
        """Find existing asset by hostname or IP in the current tenant."""
        if parsed.hostname:
            stmt = select(Asset).where(
                Asset.tenant_id == self.tenant_id,
                Asset.hostname == parsed.hostname,
            )
            result = self.db.execute(stmt).scalar_one_or_none()
            if result:
                return result

        if parsed.ip_address:
            stmt = select(Asset).where(
                Asset.tenant_id == self.tenant_id,
                Asset.ip_address == parsed.ip_address,
            )
            return self.db.execute(stmt).scalar_one_or_none()

        return None

    def _create_asset_from_parsed(self, parsed: ParsedAsset) -> Asset:
        """Create a new asset from parsed CSV data."""
        bu = self._cache["business_units"][parsed.business_unit_code]

        team_id = None
        if parsed.team_name and parsed.team_name in self._cache["teams"]:
            team_id = self._cache["teams"][parsed.team_name].id

        location_id = None
        if parsed.location_name and parsed.location_name in self._cache["locations"]:
            location_id = self._cache["locations"][parsed.location_name].id

        asset = Asset(
            tenant_id=self.tenant_id,
            name=parsed.name,
            asset_type=parsed.asset_type,
            hostname=parsed.hostname,
            ip_address=parsed.ip_address,
            business_unit_id=bu.id,
            team_id=team_id,
            location_id=location_id,
            criticality=parsed.criticality,
            owner_email=parsed.owner_email,
            is_active=parsed.is_active,
        )
        self.db.add(asset)
        self.db.flush()
        return asset

    def _update_asset_from_parsed(self, asset: Asset, parsed: ParsedAsset) -> None:
        """Update an existing asset from parsed CSV data."""
        bu = self._cache["business_units"][parsed.business_unit_code]

        asset.name = parsed.name
        asset.asset_type = parsed.asset_type
        asset.business_unit_id = bu.id
        asset.criticality = parsed.criticality
        asset.owner_email = parsed.owner_email

        if parsed.hostname:
            asset.hostname = parsed.hostname
        if parsed.ip_address:
            asset.ip_address = parsed.ip_address
        if parsed.team_name and parsed.team_name in self._cache["teams"]:
            asset.team_id = self._cache["teams"][parsed.team_name].id
        if parsed.location_name and parsed.location_name in self._cache["locations"]:
            asset.location_id = self._cache["locations"][parsed.location_name].id

        self.db.flush()

    # =========================================================================
    # Vulnerability Upload
    # =========================================================================

    def upload_vulnerabilities_csv(
        self,
        file_content: bytes,
        actor_user_id: uuid.UUID | None = None,
    ) -> ImportSummary:
        """Process vulnerability CSV upload.

        Two formats are supported:

        1) CVE catalog (no per-asset findings): columns include ``title`` and no
           ``asset_identifier`` — upserts global ``CveRecord`` rows only.

        2) Finding-oriented rows: ``cve_id`` + ``asset_identifier`` (+ optional
           status/dates/notes) to create or update ``VulnerabilityFinding`` rows.
        """
        start_time = datetime.now(timezone.utc)
        errors: list[ValidationError] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        row_count = 0

        try:
            text = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
        except Exception as e:
            raise UploadValidationError(f"Invalid CSV format: {e}") from e

        if not reader.fieldnames:
            raise UploadValidationError("CSV has no headers")

        fieldnames_lower = {f.strip().lower() for f in reader.fieldnames if f}
        rows = list(reader)
        row_count = len(rows)
        cve_catalog_mode = "title" in fieldnames_lower and "asset_identifier" not in fieldnames_lower

        if cve_catalog_mode:
            for idx, row in enumerate(rows, start=2):
                try:
                    cve_id = (row.get("cve_id") or "").strip()
                    if not cve_id or not self._is_valid_cve_id(cve_id):
                        errors.append(
                            ValidationError(
                                row_number=idx,
                                field="cve_id",
                                message=f"Invalid CVE ID: {cve_id or '(empty)'}",
                                raw_data=dict(row),
                            )
                        )
                        failed += 1
                        continue
                    cve_id_norm = cve_id.upper()
                    title = (row.get("title") or "").strip() or f"Imported: {cve_id_norm}"
                    description = (row.get("description") or "").strip() or None
                    severity = (row.get("severity") or "UNKNOWN").strip().upper() or "UNKNOWN"
                    cvss_raw = (row.get("cvss_score") or "").strip()
                    cvss_val = None
                    if cvss_raw:
                        try:
                            cvss_val = float(cvss_raw)
                        except ValueError:
                            pass

                    stmt = select(CveRecord).where(CveRecord.cve_id == cve_id_norm)
                    existing = self.db.execute(stmt).scalar_one_or_none()
                    if existing:
                        existing.title = title
                        if description is not None:
                            existing.description = description
                        existing.severity = severity
                        if cvss_val is not None:
                            existing.cvss_base_score = cvss_val
                        updated += 1
                    else:
                        cve = CveRecord(
                            cve_id=cve_id_norm,
                            title=title,
                            description=description,
                            severity=severity,
                            cvss_base_score=cvss_val,
                        )
                        self.db.add(cve)
                        inserted += 1
                    self.db.flush()
                except Exception as e:
                    errors.append(
                        ValidationError(
                            row_number=idx,
                            message=f"Unexpected error: {str(e)}",
                            raw_data=dict(row),
                        )
                    )
                    failed += 1

            self.db.commit()

            if actor_user_id and (inserted + updated) > 0:
                self.audit.record(
                    actor_user_id=actor_user_id,
                    action="upload.vulnerabilities",
                    resource_type="import",
                    resource_id=str(uuid.uuid4()),
                    payload={
                        "inserted": inserted,
                        "updated": updated,
                        "failed": failed,
                        "rows_processed": row_count,
                        "mode": "cve_catalog",
                    },
                )
                self.db.commit()

            processing_time = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            return ImportSummary(
                total_rows=row_count,
                inserted=inserted,
                updated=updated,
                failed=failed,
                skipped=skipped,
                errors=errors[:100],
                processing_time_ms=processing_time,
                imported_at=datetime.now(timezone.utc),
            )

        self._preload_tenant_cache()

        for row_num, row in enumerate(rows, start=2):
            try:
                parsed = self._parse_vulnerability_row(row, row_num, errors)
                if parsed is None:
                    failed += 1
                    continue

                asset = self._find_asset_by_identifier(parsed.asset_identifier)
                if not asset:
                    errors.append(
                        ValidationError(
                            row_number=row_num,
                            field="asset_identifier",
                            message=f"Asset not found: {parsed.asset_identifier}",
                            raw_data=row,
                        )
                    )
                    failed += 1
                    continue

                cve = self._get_or_create_cve_record(parsed.cve_id)

                existing = self._find_existing_finding(asset.id, cve.id)

                if existing:
                    self._update_finding_from_parsed(existing, parsed)
                    updated += 1
                else:
                    self._create_finding_from_parsed(asset, cve, parsed)
                    inserted += 1

            except Exception as e:
                errors.append(
                    ValidationError(
                        row_number=row_num,
                        message=f"Unexpected error: {str(e)}",
                        raw_data=row,
                    )
                )
                failed += 1

        self.db.commit()

        if actor_user_id and (inserted + updated) > 0:
            self.audit.record(
                actor_user_id=actor_user_id,
                action="upload.vulnerabilities",
                resource_type="import",
                resource_id=str(uuid.uuid4()),
                payload={
                    "inserted": inserted,
                    "updated": updated,
                    "failed": failed,
                    "rows_processed": row_count,
                },
            )
            self.db.commit()

        processing_time = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )

        return ImportSummary(
            total_rows=row_count,
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            errors=errors[:100],
            processing_time_ms=processing_time,
            imported_at=datetime.now(timezone.utc),
        )

    def _parse_vulnerability_row(
        self,
        row: dict[str, str],
        row_num: int,
        errors: list[ValidationError],
    ) -> ParsedVulnerability | None:
        """Parse and validate a vulnerability row."""
        cve_id = row.get("cve_id", "").strip()
        if not cve_id:
            errors.append(ValidationError(
                row_number=row_num,
                field="cve_id",
                message="CVE ID is required",
                raw_data=row,
            ))
            return None

        if not self._is_valid_cve_id(cve_id):
            errors.append(ValidationError(
                row_number=row_num,
                field="cve_id",
                message=f"Invalid CVE ID format: {cve_id}",
                raw_data=row,
            ))
            return None

        asset_identifier = row.get("asset_identifier", "").strip()
        if not asset_identifier:
            errors.append(ValidationError(
                row_number=row_num,
                field="asset_identifier",
                message="Asset identifier (hostname or IP) is required",
                raw_data=row,
            ))
            return None

        status = row.get("status", "OPEN").strip().upper()
        valid_statuses = ["OPEN", "IN_PROGRESS", "REMEDIATED", "ACCEPTED_RISK", "FALSE_POSITIVE"]
        if status not in valid_statuses:
            errors.append(ValidationError(
                row_number=row_num,
                field="status",
                message=f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}",
                raw_data=row,
            ))
            return None

        # Parse dates
        discovered_at = None
        due_at = None

        if row.get("discovered_date"):
            try:
                discovered_at = datetime.fromisoformat(row["discovered_date"].strip())
            except ValueError:
                errors.append(ValidationError(
                    row_number=row_num,
                    field="discovered_date",
                    message=f"Invalid date format: {row['discovered_date']}",
                    raw_data=row,
                ))
                return None

        if row.get("due_date"):
            try:
                due_at = datetime.fromisoformat(row["due_date"].strip())
            except ValueError:
                errors.append(ValidationError(
                    row_number=row_num,
                    field="due_date",
                    message=f"Invalid date format: {row['due_date']}",
                    raw_data=row,
                ))
                return None

        assigned_to_email = row.get("assigned_to_email", "").strip() or None
        if assigned_to_email and not self._is_valid_email(assigned_to_email):
            errors.append(ValidationError(
                row_number=row_num,
                field="assigned_to_email",
                message=f"Invalid email: {assigned_to_email}",
                raw_data=row,
            ))
            return None

        return ParsedVulnerability(
            cve_id=cve_id.upper(),
            asset_identifier=asset_identifier,
            status=status,
            discovered_at=discovered_at,
            due_at=due_at,
            notes=row.get("notes", "").strip() or None,
            assigned_to_email=assigned_to_email,
        )

    def _find_asset_by_identifier(self, identifier: str) -> Asset | None:
        """Find asset by hostname or IP in the current tenant."""
        # Try hostname first
        stmt = select(Asset).where(
            Asset.tenant_id == self.tenant_id,
            Asset.hostname == identifier,
        )
        result = self.db.execute(stmt).scalar_one_or_none()
        if result:
            return result

        # Try IP address
        stmt = select(Asset).where(
            Asset.tenant_id == self.tenant_id,
            Asset.ip_address == identifier,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def _get_or_create_cve_record(self, cve_id: str) -> CveRecord:
        """Get existing CVE record or create placeholder."""
        stmt = select(CveRecord).where(CveRecord.cve_id == cve_id.upper())
        cve = self.db.execute(stmt).scalar_one_or_none()

        if not cve:
            # Create placeholder CVE record
            cve = CveRecord(
                cve_id=cve_id.upper(),
                title=f"Imported: {cve_id}",
                severity="UNKNOWN",
            )
            self.db.add(cve)
            self.db.flush()

        return cve

    def _find_existing_finding(
        self,
        asset_id: uuid.UUID,
        cve_record_id: uuid.UUID,
    ) -> VulnerabilityFinding | None:
        """Find existing vulnerability finding for asset/CVE combination."""
        stmt = select(VulnerabilityFinding).where(
            VulnerabilityFinding.tenant_id == self.tenant_id,
            VulnerabilityFinding.asset_id == asset_id,
            VulnerabilityFinding.cve_record_id == cve_record_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def _create_finding_from_parsed(
        self,
        asset: Asset,
        cve: CveRecord,
        parsed: ParsedVulnerability,
    ) -> VulnerabilityFinding:
        """Create a new vulnerability finding."""
        # Resolve assigned user if email provided
        assigned_to_user_id = None
        if parsed.assigned_to_email and parsed.assigned_to_email in self._cache.get("users", {}):
            assigned_to_user_id = self._cache["users"][parsed.assigned_to_email].id

        finding = VulnerabilityFinding(
            tenant_id=self.tenant_id,
            asset_id=asset.id,
            cve_record_id=cve.id,
            status=parsed.status,
            discovered_at=parsed.discovered_at or datetime.now(timezone.utc),
            due_at=parsed.due_at,
            notes=parsed.notes,
            assigned_to_user_id=assigned_to_user_id,
        )
        self.db.add(finding)
        self.db.flush()
        return finding

    def _update_finding_from_parsed(
        self,
        finding: VulnerabilityFinding,
        parsed: ParsedVulnerability,
    ) -> None:
        """Update existing vulnerability finding."""
        finding.status = parsed.status
        if parsed.due_at:
            finding.due_at = parsed.due_at
        if parsed.notes:
            finding.notes = parsed.notes
        if parsed.assigned_to_email and parsed.assigned_to_email in self._cache.get("users", {}):
            finding.assigned_to_user_id = self._cache["users"][parsed.assigned_to_email].id
        self.db.flush()

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _persist_import_metadata(
        self,
        *,
        upload_type: str,
        original_filename: str | None,
        file_size_bytes: int | None,
        mime_type: str | None,
        summary: ImportSummary,
        actor_user_id: uuid.UUID | None = None,
    ) -> None:
        """Persist upload metadata for audit/governance dashboards."""
        status = "completed" if summary.failed == 0 else ("partial" if (summary.inserted + summary.updated) > 0 else "failed")
        payload = {
            "total_rows": summary.total_rows,
            "inserted": summary.inserted,
            "updated": summary.updated,
            "failed": summary.failed,
            "skipped": summary.skipped,
            "processing_time_ms": summary.processing_time_ms,
            "errors": [err.model_dump() for err in summary.errors],
        }
        record = UploadImport(
            tenant_id=self.tenant_id,
            uploaded_by_user_id=actor_user_id,
            upload_type=upload_type,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            status=status,
            summary=payload,
            processing_time_ms=summary.processing_time_ms,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Validate IP address format (IPv4 or IPv6)."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Basic email validation."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def _is_valid_cve_id(cve_id: str) -> bool:
        """Validate CVE identifier (e.g. CVE-2024-1234)."""
        if not cve_id or not str(cve_id).strip():
            return False
        return bool(re.match(r"^CVE-\d{4}-\d{4,}$", str(cve_id).strip(), re.IGNORECASE))

    def _parse_date(self, value: str | None) -> datetime | None:
        """Parse date from CSV (ISO or YYYY-MM-DD)."""
        if not value or not str(value).strip():
            return None
        raw = str(value).strip()
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
        try:
            return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    # =========================================================================
    # JSON Upload Methods
    # =========================================================================

    def upload_assets_json(
        self,
        file_content: bytes,
        actor_user_id: uuid.UUID | None = None,
    ) -> ImportSummary:
        """Process asset JSON upload with tenant-aware insertion."""
        import json
        
        start_time = datetime.now(timezone.utc)
        errors: list[ValidationError] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        
        try:
            data = json.loads(file_content.decode("utf-8"))
            if not isinstance(data, list):
                raise UploadValidationError("JSON must be an array of objects")
        except json.JSONDecodeError as e:
            raise UploadValidationError(f"Invalid JSON: {e}") from e
        except UnicodeDecodeError as e:
            raise UploadValidationError("File must be UTF-8 encoded") from e
        
        # Pre-load tenant data for validation
        self._preload_tenant_cache()
        
        total_rows = len(data)

        for row_num, row in enumerate(data, start=1):
            try:
                row_str = {
                    str(k): ("" if v is None else str(v))
                    for k, v in (row if isinstance(row, dict) else {}).items()
                }
                row_errors: list[ValidationError] = []
                parsed = self._parse_asset_row(row_str, row_num, row_errors)
                if parsed is None:
                    failed += 1
                    errors.extend(row_errors)
                    continue

                existing = self._find_existing_asset(parsed)
                if existing:
                    self._update_asset_from_parsed(existing, parsed)
                    updated += 1
                else:
                    self._create_asset_from_parsed(parsed)
                    inserted += 1

            except Exception as e:
                errors.append(
                    ValidationError(
                        row_number=row_num,
                        message=f"Unexpected error: {str(e)}",
                        raw_data=row if isinstance(row, dict) else {},
                    )
                )
                failed += 1

        self.db.commit()
        
        # Audit log
        if actor_user_id:
            self.audit.record(
                actor_user_id=actor_user_id,
                action="ASSETS_UPLOAD_JSON",
                resource_type="upload",
                resource_id=str(uuid.uuid4()),
                payload={
                    "inserted": inserted,
                    "updated": updated,
                    "failed": failed,
                    "total": total_rows,
                },
            )
        
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ImportSummary(
            total_rows=total_rows,
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            errors=errors,
            processing_time_ms=processing_time,
            imported_at=datetime.now(timezone.utc),
        )

    def upload_vulnerabilities_json(
        self,
        file_content: bytes,
        actor_user_id: uuid.UUID | None = None,
    ) -> ImportSummary:
        """Process vulnerability JSON upload."""
        import json
        
        start_time = datetime.now(timezone.utc)
        errors: list[ValidationError] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        
        try:
            data = json.loads(file_content.decode("utf-8"))
            if not isinstance(data, list):
                raise UploadValidationError("JSON must be an array of objects")
        except json.JSONDecodeError as e:
            raise UploadValidationError(f"Invalid JSON: {e}") from e
        except UnicodeDecodeError as e:
            raise UploadValidationError("File must be UTF-8 encoded") from e
        
        total_rows = len(data)
        
        for row_num, row in enumerate(data, start=1):
            try:
                cve_id = row.get("cve_id", "").strip().upper()
                if not cve_id or not self._is_valid_cve_id(cve_id):
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="cve_id",
                        message="Valid CVE ID is required (e.g., CVE-2024-1234)",
                        raw_data=row,
                    ))
                    failed += 1
                    continue
                
                # Check for existing CVE record
                stmt = select(CveRecord).where(CveRecord.cve_id == cve_id)
                existing = self.db.execute(stmt).scalar_one_or_none()
                
                if existing:
                    # Update existing record
                    if row.get("title"):
                        existing.title = row["title"]
                    if row.get("description"):
                        existing.description = row["description"]
                    if row.get("severity"):
                        existing.severity = row["severity"].upper()
                    if row.get("cvss_score"):
                        try:
                            existing.cvss_base_score = float(row["cvss_score"])
                        except ValueError:
                            pass
                    updated += 1
                else:
                    # Create new CVE record
                    cve = CveRecord(
                        cve_id=cve_id,
                        title=row.get("title", f"Imported: {cve_id}"),
                        description=row.get("description"),
                        severity=row.get("severity", "UNKNOWN").upper(),
                    )
                    if row.get("cvss_score"):
                        try:
                            cve.cvss_base_score = float(row["cvss_score"])
                        except ValueError:
                            pass
                    self.db.add(cve)
                    inserted += 1
                    
            except Exception as e:
                errors.append(ValidationError(
                    row_number=row_num,
                    message=f"Unexpected error: {str(e)}",
                    raw_data=row,
                ))
                failed += 1
        
        self.db.commit()
        
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ImportSummary(
            total_rows=total_rows,
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            errors=errors,
            processing_time_ms=processing_time,
            imported_at=datetime.now(timezone.utc),
        )

    def upload_mappings_csv(
        self,
        file_content: bytes,
        actor_user_id: uuid.UUID | None = None,
    ) -> ImportSummary:
        """Process asset-vulnerability mapping CSV upload."""
        start_time = datetime.now(timezone.utc)
        errors: list[ValidationError] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        
        try:
            text = file_content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(text))
        except UnicodeDecodeError as e:
            raise UploadValidationError("File must be UTF-8 encoded") from e
        except Exception as e:
            raise UploadValidationError(f"Invalid CSV format: {e}") from e
        
        if not reader.fieldnames:
            raise UploadValidationError("CSV has no headers")
        
        # Pre-load tenant data
        self._preload_tenant_cache()
        
        row_count = 0
        
        for row in reader:
            row_count += 1
            row_num = row_count + 1  # 1-indexed for user feedback
            
            try:
                # Validate required fields
                asset_identifier = row.get("asset_identifier", "").strip()
                cve_id = row.get("cve_id", "").strip().upper()
                
                if not asset_identifier:
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="asset_identifier",
                        message="Asset identifier (hostname or IP) is required",
                        raw_data=dict(row),
                    ))
                    failed += 1
                    continue
                
                if not cve_id or not self._is_valid_cve_id(cve_id):
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="cve_id",
                        message="Valid CVE ID is required (e.g., CVE-2024-1234)",
                        raw_data=dict(row),
                    ))
                    failed += 1
                    continue
                
                # Find asset by identifier
                asset = self._find_asset_by_identifier(asset_identifier)
                if not asset:
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="asset_identifier",
                        message=f"Asset '{asset_identifier}' not found in this tenant",
                        raw_data=dict(row),
                    ))
                    failed += 1
                    continue
                
                # Get or create CVE record
                cve = self._get_or_create_cve_record(cve_id)
                
                # Check for existing finding
                existing = self._find_existing_finding(asset.id, cve.id)
                
                # Parse status
                status = row.get("status", "OPEN").strip().upper()
                valid_statuses = {"OPEN", "IN_PROGRESS", "REMEDIATED", "ACCEPTED_RISK", "FALSE_POSITIVE"}
                if status not in valid_statuses:
                    status = "OPEN"
                
                # Parse dates
                discovered_at = None
                due_at = None
                
                if row.get("discovered_date"):
                    discovered_at = self._parse_date(row["discovered_date"])
                
                if row.get("due_date"):
                    due_at = self._parse_date(row["due_date"])
                
                # Get notes and assigned user
                notes = row.get("notes")
                assigned_to_email = row.get("assigned_to_email")
                
                if existing:
                    # Update existing finding
                    existing.status = status
                    if discovered_at:
                        existing.discovered_at = discovered_at
                    if due_at:
                        existing.due_at = due_at
                    if notes:
                        existing.notes = notes
                    if assigned_to_email and assigned_to_email in self._cache.get("users", {}):
                        existing.assigned_to_user_id = self._cache["users"][assigned_to_email].id
                    updated += 1
                else:
                    # Create new finding
                    finding = VulnerabilityFinding(
                        tenant_id=self.tenant_id,
                        asset_id=asset.id,
                        cve_record_id=cve.id,
                        status=status,
                        discovered_at=discovered_at or datetime.now(timezone.utc),
                        due_at=due_at,
                        notes=notes,
                    )
                    if assigned_to_email and assigned_to_email in self._cache.get("users", {}):
                        finding.assigned_to_user_id = self._cache["users"][assigned_to_email].id
                    self.db.add(finding)
                    inserted += 1
                
                self.db.flush()
                
            except Exception as e:
                errors.append(ValidationError(
                    row_number=row_num,
                    message=f"Unexpected error: {str(e)}",
                    raw_data=dict(row),
                ))
                failed += 1
        
        self.db.commit()
        
        # Audit log
        if actor_user_id:
            self.audit.record(
                actor_user_id=actor_user_id,
                action="MAPPINGS_UPLOAD_CSV",
                resource_type="upload",
                resource_id=str(uuid.uuid4()),
                payload={
                    "inserted": inserted,
                    "updated": updated,
                    "failed": failed,
                    "total": row_count,
                },
            )
        
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ImportSummary(
            total_rows=row_count,
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            errors=errors,
            processing_time_ms=processing_time,
            imported_at=datetime.now(timezone.utc),
        )

    def upload_mappings_json(
        self,
        file_content: bytes,
        actor_user_id: uuid.UUID | None = None,
    ) -> ImportSummary:
        """Process asset-vulnerability mapping JSON upload."""
        import json
        
        start_time = datetime.now(timezone.utc)
        errors: list[ValidationError] = []
        inserted = 0
        updated = 0
        failed = 0
        skipped = 0
        
        try:
            data = json.loads(file_content.decode("utf-8"))
            if not isinstance(data, list):
                raise UploadValidationError("JSON must be an array of objects")
        except json.JSONDecodeError as e:
            raise UploadValidationError(f"Invalid JSON: {e}") from e
        except UnicodeDecodeError as e:
            raise UploadValidationError("File must be UTF-8 encoded") from e
        
        # Pre-load tenant data
        self._preload_tenant_cache()
        
        total_rows = len(data)
        
        for row_num, row in enumerate(data, start=1):
            try:
                asset_identifier = row.get("asset_identifier", "").strip()
                cve_id = row.get("cve_id", "").strip().upper()
                
                if not asset_identifier:
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="asset_identifier",
                        message="Asset identifier is required",
                        raw_data=row,
                    ))
                    failed += 1
                    continue
                
                if not cve_id or not self._is_valid_cve_id(cve_id):
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="cve_id",
                        message="Valid CVE ID is required",
                        raw_data=row,
                    ))
                    failed += 1
                    continue
                
                # Find asset
                asset = self._find_asset_by_identifier(asset_identifier)
                if not asset:
                    errors.append(ValidationError(
                        row_number=row_num,
                        field="asset_identifier",
                        message=f"Asset '{asset_identifier}' not found",
                        raw_data=row,
                    ))
                    failed += 1
                    continue
                
                # Get or create CVE
                cve = self._get_or_create_cve_record(cve_id)
                
                # Check for existing finding
                existing = self._find_existing_finding(asset.id, cve.id)
                
                # Parse status
                status_str = row.get("status", "OPEN").upper()
                valid_statuses = {"OPEN", "IN_PROGRESS", "REMEDIATED", "ACCEPTED_RISK", "FALSE_POSITIVE"}
                if status_str not in valid_statuses:
                    status_str = "OPEN"
                
                if existing:
                    existing.status = status_str
                    updated += 1
                else:
                    finding = VulnerabilityFinding(
                        tenant_id=self.tenant_id,
                        asset_id=asset.id,
                        cve_record_id=cve.id,
                        status=status_str,
                        discovered_at=datetime.now(timezone.utc),
                    )
                    self.db.add(finding)
                    inserted += 1
                
            except Exception as e:
                errors.append(ValidationError(
                    row_number=row_num,
                    message=f"Unexpected error: {str(e)}",
                    raw_data=row,
                ))
                failed += 1
        
        self.db.commit()
        
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ImportSummary(
            total_rows=total_rows,
            inserted=inserted,
            updated=updated,
            failed=failed,
            skipped=skipped,
            errors=errors,
            processing_time_ms=processing_time,
            imported_at=datetime.now(timezone.utc),
        )
