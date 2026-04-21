"""Secure file upload endpoints for vulnerability reports, scan results, etc."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import AdminDep, TenantContextDep, WriterDep
from app.db.deps import get_db
from app.schemas.common import ErrorResponse
from app.services.audit_service import AuditService
from app.services.file_validation_service import (
    FileValidationError,
    FileValidationService,
)
from app.services.secure_storage_service import get_storage_service
from app.services.virus_scan_service import ScanResult, get_virus_scan_service

router = APIRouter()
logger = logging.getLogger(__name__)

# Maximum file size
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload", response_model=dict)
async def upload_file(
    principal: WriterDep,
    tenant_context: TenantContextDep,
    file: Annotated[UploadFile, File()],
    description: str | None = None,
    upload_type: str = "document",
    db: Session = Depends(get_db),
) -> dict:
    """Upload a vulnerability scan result or report file with security validation.

    Security features:
    - File type validation (extension + MIME type detection)
    - Content structure validation (CSV/JSON schema)
    - Virus scanning (ClamAV)
    - Secure tenant-isolated storage
    - Path traversal protection

    Allowed types: .csv, .json, .xml, .nessus, .sarif, .pdf, .zip
    Max size: 50MB
    """
    # STEP 1: File Validation (type, size, structure)
    try:
        content, ext, detected_mime = await FileValidationService.validate_upload(
            file, validate_structure=True
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # STEP 2: Virus Scanning
    virus_scanner = get_virus_scan_service()
    scan_report = await virus_scanner.scan_bytes(content)

    if scan_report.result == ScanResult.INFECTED:
        # Log security event
        audit = AuditService(db)
        audit.record(
            actor_user_id=principal.id,
            action="FILE_UPLOAD_BLOCKED",
            resource_type="upload",
            resource_id="blocked",
            tenant_id=tenant_context.tenant_id,
            payload={
                "original_filename": file.filename,
                "reason": "virus_detected",
                "threat": scan_report.threat_found,
                "upload_type": upload_type,
            },
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security threat detected: {scan_report.threat_found}. Upload blocked.",
        )

    if scan_report.result == ScanResult.ERROR:
        # Log but don't block (scanning failure shouldn't break uploads)
        logger = logging.getLogger(__name__)
        logger.warning(f"Virus scan error: {scan_report.error_message}")

    # STEP 3: Secure Storage
    storage = get_storage_service()
    file_id = str(uuid.uuid4())

    try:
        abs_path, storage_relative_path, file_hash = storage.store_file(
            tenant_id=tenant_context.tenant_id,
            content=content,
            original_filename=file.filename or "unknown",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}",
        )

    # STEP 4: Persist Metadata
    from app.models.oltp import UploadFile as UploadFileModel

    upload_record = UploadFileModel(
        id=uuid.UUID(file_id),
        tenant_id=tenant_context.tenant_id,
        uploaded_by_user_id=principal.id,
        upload_type=upload_type,
        original_filename=file.filename or "unknown",
        storage_path=storage_relative_path,
        file_size_bytes=len(content),
        mime_type=detected_mime,
        description=description,
        # Additional security fields
        file_hash=file_hash,
        scan_status=scan_report.result.value,
        scan_threat=scan_report.threat_found,
    )
    db.add(upload_record)
    db.commit()

    # STEP 5: Audit Logging
    audit = AuditService(db)
    audit.record(
        actor_user_id=principal.id,
        action="FILE_UPLOAD",
        resource_type="upload",
        resource_id=file_id,
        tenant_id=tenant_context.tenant_id,
        payload={
            "original_filename": file.filename,
            "saved_as": storage_relative_path,
            "size": len(content),
            "hash": file_hash,
            "mime_type": detected_mime,
            "scan_result": scan_report.result.value,
            "scan_time_ms": scan_report.scan_time_ms,
            "description": description,
            "upload_type": upload_type,
        },
    )
    db.commit()

    return {
        "id": file_id,
        "original_filename": file.filename,
        "saved_filename": Path(storage_relative_path).name,
        "storage_path": storage_relative_path,
        "size": len(content),
        "hash": file_hash,
        "mime_type": detected_mime,
        "scan_result": scan_report.result.value,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "message": "File uploaded and scanned successfully",
    }


@router.get("/uploads/{file_id}")
async def download_file(
    file_id: str,
    principal: WriterDep,
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download an uploaded file with secure path validation.

    Uses secure storage service to validate path and prevent traversal attacks.
    """
    from app.models.oltp import UploadFile as UploadFileModel

    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file ID",
        ) from exc

    upload_record = db.query(UploadFileModel).filter(UploadFileModel.id == file_uuid).first()

    if not upload_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Verify tenant access (platform owners may access all tenant uploads)
    if not principal.is_platform_owner and upload_record.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Use secure storage service for path validation
    storage = get_storage_service()
    try:
        file_path = storage.retrieve_file(
            tenant_id=upload_record.tenant_id,
            storage_path=upload_record.storage_path,
        )
    except Exception as e:
        logger.error(f"File retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or access denied"
        )

    return FileResponse(
        path=file_path,
        filename=upload_record.original_filename,
        media_type=upload_record.mime_type or "application/octet-stream"
    )


@router.delete("/uploads/{file_id}", response_model=dict)
async def delete_file(
    file_id: str,
    principal: AdminDep,
    db: Session = Depends(get_db),
) -> dict:
    """Delete an uploaded file (admin only) with secure path validation.

    Uses secure storage service to validate path before deletion.
    """
    from app.models.oltp import UploadFile as UploadFileModel

    try:
        file_uuid = uuid.UUID(file_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file ID",
        ) from exc

    upload_record = db.query(UploadFileModel).filter(UploadFileModel.id == file_uuid).first()

    if not upload_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    # Verify tenant access (platform owners may access all tenant uploads)
    if not principal.is_platform_owner and upload_record.tenant_id != principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Use secure storage service for path validation and deletion
    storage = get_storage_service()
    try:
        storage.delete_file(
            tenant_id=upload_record.tenant_id,
            storage_path=upload_record.storage_path,
        )
    except Exception as e:
        logger.error(f"File deletion failed: {e}")
        # Continue to delete database record even if file is missing

    # Delete database record
    db.delete(upload_record)

    # Audit log
    audit = AuditService(db)
    audit.record(
        actor_user_id=principal.id,
        action="FILE_DELETE",
        resource_type="upload",
        resource_id=file_id,
        tenant_id=upload_record.tenant_id,
    )
    db.commit()

    return {"message": "File deleted successfully"}


@router.get("/uploads", response_model=dict)
async def list_uploads(
    principal: WriterDep,
    tenant_context: TenantContextDep,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """List uploaded files for current tenant.

    Uses database metadata for tenant-scoped file listing.
    """
    from app.models.oltp import UploadFile as UploadFileModel

    query = db.query(UploadFileModel).filter(UploadFileModel.tenant_id == tenant_context.tenant_id)

    total = query.count()
    uploads = query.order_by(UploadFileModel.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(u.id),
                "upload_type": u.upload_type,
                "original_filename": u.original_filename,
                "file_size_bytes": u.file_size_bytes,
                "mime_type": u.mime_type,
                "description": u.description,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in uploads
        ],
    }
