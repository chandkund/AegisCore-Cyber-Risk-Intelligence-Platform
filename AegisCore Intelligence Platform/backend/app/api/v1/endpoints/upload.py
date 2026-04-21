"""API endpoints for tenant-aware data uploads.

These endpoints allow company admins to upload CSV/JSON files for:
- Assets (CSV, JSON)
- Vulnerabilities (CSV, JSON)
- Asset-vulnerability mappings (CSV, JSON)

All uploads are strictly scoped to the authenticated user's tenant.
Each endpoint returns detailed import summaries including validation errors.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import AdminDep, TenantContextDep, WriterDep
from app.core.tenant import TenantContext
from app.db.deps import get_db
from app.schemas.upload import (
    AssetUploadResponse,
    MappingUploadResponse,
    VulnerabilityUploadResponse,
)
from app.services.upload_service import UploadService, UploadValidationError
from app.services.secure_upload_pipeline import secure_upload, SecureUploadError
from app.services.audit_service import AuditService

router = APIRouter(prefix="/upload", tags=["upload"])


def _upload_response_from_summary(
    summary,
    entity_type: str,
) -> dict:
    """Generate standardized upload response from import summary."""
    total_processed = summary.inserted + summary.updated + summary.failed
    
    if summary.failed == 0:
        message = f"Successfully imported {summary.inserted} {entity_type}"
        if summary.updated > 0:
            message += f", updated {summary.updated}"
        success = True
    elif summary.inserted > 0 or summary.updated > 0:
        message = f"Partial import: {summary.inserted} inserted, {summary.updated} updated, {summary.failed} failed"
        success = True
    else:
        message = f"Import failed: {summary.failed} errors, no records imported"
        success = False

    return {
        "success": success,
        "message": message,
        "summary": summary,
        "import_id": str(uuid.uuid4()),
    }


async def _secure_validate_and_store(
    file: UploadFile,
    tenant: TenantContext,
    allowed_extensions: set[str],
    max_size_mb: int = 10,
) -> dict:
    """Securely validate and store uploaded file.
    
    Performs:
    1. Extension validation
    2. MIME type validation (magic numbers)
    3. Size validation
    4. Virus scanning
    5. Structure validation (CSV/JSON)
    6. Secure storage with tenant isolation
    
    Returns:
        Dict with file_id, stored_path, size, etc.
        
    Raises:
        HTTPException: If validation or scanning fails
    """
    try:
        result = await secure_upload(
            file=file,
            tenant=tenant,
            allowed_extensions=allowed_extensions,
            max_size_mb=max_size_mb,
        )
        return {
            "file_id": result.file_id,
            "stored_path": result.stored_path,
            "size_bytes": result.size_bytes,
            "mime_type": result.mime_type,
            "scan_status": result.scan_status,
        }
    except SecureUploadError as e:
        raise HTTPException(
            status_code=e.status_code or status.HTTP_400_BAD_REQUEST,
            detail=f"Upload failed at {e.stage}: {e.message}",
        )


@router.post(
    "/assets",
    response_model=AssetUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_assets(
    principal: AdminDep,  # Only admins can bulk import assets
    tenant_context: TenantContextDep,
    file: Annotated[UploadFile, File(description="CSV or JSON file with asset data")],
    db: Session = Depends(get_db),
):
    """Upload assets CSV or JSON file.
    
    Expected CSV format:
    - name (required): Asset name
    - asset_type (required): Type of asset (server, workstation, etc.)
    - hostname (optional): Hostname
    - ip_address (optional): IP address
    - business_unit_code (required): Code of existing business unit
    - team_name (optional): Name of existing team
    - location_name (optional): Name of existing location
    - criticality (optional): 1-5, default 3
    - owner_email (optional): Email of asset owner
    
    Expected JSON format:
    Array of objects with same fields as CSV columns.
    
    Existing assets (matched by hostname or IP) will be updated.
    New assets will be created.
    
    Returns import summary with inserted, updated, failed counts and errors.
    """
    # Secure upload pipeline: validation + virus scan + storage
    upload_result = await _secure_validate_and_store(
        file, tenant_context, {"csv", "json"}, max_size_mb=10
    )

    try:
        content = await file.read()

        service = UploadService(db, tenant_context)

        # Determine format from extension
        ext = file.filename.split(".")[-1].lower()
        if ext == "json":
            summary = service.upload_assets_json(content, actor_user_id=principal.id)
        else:
            summary = service.upload_assets_csv(content, actor_user_id=principal.id)

        # Persist import metadata for audit and governance
        service._persist_import_metadata(
            upload_type="assets_import",
            original_filename=file.filename,
            file_size_bytes=len(content),
            mime_type=file.content_type,
            summary=summary,
            actor_user_id=principal.id,
        )

        return _upload_response_from_summary(summary, "assets")

    except UploadValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        ) from e
    finally:
        await file.close()


@router.post(
    "/vulnerabilities",
    response_model=VulnerabilityUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_vulnerabilities(
    principal: WriterDep,
    tenant_context: TenantContextDep,
    file: Annotated[UploadFile, File(description="CSV or JSON file with vulnerability data")],
    db: Session = Depends(get_db),
):
    """Upload vulnerabilities CSV or JSON file.
    
    Expected CSV/JSON format:
    - cve_id (required): CVE identifier (e.g., CVE-2024-1234)
    - title (required): Vulnerability title
    - description (optional): Full description
    - severity (optional): CRITICAL, HIGH, MEDIUM, LOW, INFO
    - cvss_score (optional): 0.0 - 10.0
    - cvss_vector (optional): CVSS vector string
    - exploit_available (optional): true/false
    - published_date (optional): ISO date format
    
    CVE records will be created or updated based on CVE ID.
    
    Returns import summary with inserted, updated, failed counts and errors.
    """
    # Secure upload pipeline: validation + virus scan + storage
    upload_result = await _secure_validate_and_store(
        file, tenant_context, {"csv", "json"}, max_size_mb=10
    )

    try:
        content = await file.read()

        service = UploadService(db, tenant_context)

        ext = file.filename.split(".")[-1].lower()
        if ext == "json":
            summary = service.upload_vulnerabilities_json(content, actor_user_id=principal.id)
        else:
            summary = service.upload_vulnerabilities_csv(content, actor_user_id=principal.id)

        # Persist import metadata for audit and governance
        service._persist_import_metadata(
            upload_type="vulnerabilities_import",
            original_filename=file.filename,
            file_size_bytes=len(content),
            mime_type=file.content_type,
            summary=summary,
            actor_user_id=principal.id,
        )

        return _upload_response_from_summary(summary, "vulnerabilities")

    except UploadValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        ) from e
    finally:
        await file.close()


@router.post(
    "/mappings",
    response_model=MappingUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_mappings(
    principal: WriterDep,
    tenant_context: TenantContextDep,
    file: Annotated[UploadFile, File(description="CSV or JSON file with asset-vulnerability mappings")],
    db: Session = Depends(get_db),
):
    """Upload asset-vulnerability mapping CSV or JSON file.
    
    Creates vulnerability findings by linking assets to CVEs.
    
    Expected CSV/JSON format:
    - asset_identifier (required): Hostname or IP of existing asset
    - cve_id (required): CVE identifier (e.g., CVE-2024-1234)
    - status (optional): OPEN, IN_PROGRESS, REMEDIATED, ACCEPTED_RISK, FALSE_POSITIVE (default: OPEN)
    - discovered_date (optional): ISO date format (default: today)
    - due_date (optional): ISO date format
    - severity_override (optional): Override CVE severity
    - notes (optional): Free text notes
    - assigned_to_email (optional): Email of assignee
    
    Assets are matched by hostname or IP within the authenticated tenant.
    CVE records are matched by CVE ID.
    
    Returns import summary with inserted, updated, failed counts and errors.
    """
    # Secure upload pipeline: validation + virus scan + storage
    upload_result = await _secure_validate_and_store(
        file, tenant_context, {"csv", "json"}, max_size_mb=10
    )

    try:
        content = await file.read()

        service = UploadService(db, tenant_context)

        ext = file.filename.split(".")[-1].lower()
        if ext == "json":
            summary = service.upload_mappings_json(content, actor_user_id=principal.id)
        else:
            summary = service.upload_mappings_csv(content, actor_user_id=principal.id)

        # Persist import metadata for audit and governance
        service._persist_import_metadata(
            upload_type="mappings_import",
            original_filename=file.filename,
            file_size_bytes=len(content),
            mime_type=file.content_type,
            summary=summary,
            actor_user_id=principal.id,
        )

        return _upload_response_from_summary(summary, "mappings")

    except UploadValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}",
        ) from e
    finally:
        await file.close()


@router.get("/templates/{template_type}")
def get_upload_template(
    principal: WriterDep,
    template_type: str,  # "assets" | "vulnerabilities" | "mappings"
):
    """Download CSV template for upload.
    
    Returns a CSV template with the correct headers and example data.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse

    templates = {
        "assets": {
            "headers": [
                "name",
                "asset_type",
                "hostname",
                "ip_address",
                "business_unit_code",
                "team_name",
                "location_name",
                "criticality",
                "owner_email",
            ],
            "example": [
                "Web Server 01",
                "server",
                "web01.example.com",
                "192.168.1.10",
                "engineering",
                "platform-team",
                "us-east",
                "4",
                "admin@example.com",
            ],
        },
        "vulnerabilities": {
            "headers": [
                "cve_id",
                "title",
                "description",
                "severity",
                "cvss_score",
                "exploit_available",
                "published_date",
            ],
            "example": [
                "CVE-2024-1234",
                "SQL Injection in Login Form",
                "Unsanitized user input allows SQL injection attacks",
                "CRITICAL",
                "9.8",
                "true",
                "2024-01-15",
            ],
        },
        "mappings": {
            "headers": [
                "asset_identifier",
                "cve_id",
                "status",
                "discovered_date",
                "due_date",
                "severity_override",
                "notes",
                "assigned_to_email",
            ],
            "example": [
                "web01.example.com",
                "CVE-2024-1234",
                "OPEN",
                "2024-01-15",
                "2024-02-15",
                "",
                "Found during Q1 security scan",
                "security@example.com",
            ],
        },
    }
    
    if template_type not in templates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown template type: {template_type}. Allowed: {', '.join(templates.keys())}",
        )
    
    template = templates[template_type]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(template["headers"])
    writer.writerow(template["example"])

    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={template_type}_template.csv"
        },
    )
