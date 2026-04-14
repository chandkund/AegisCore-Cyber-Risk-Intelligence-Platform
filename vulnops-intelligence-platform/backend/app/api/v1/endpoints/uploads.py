"""File upload endpoints for vulnerability reports, scan results, etc."""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import AdminDep, WriterDep
from app.db.deps import get_db
from app.schemas.common import ErrorResponse
from app.services.audit_service import AuditService

router = APIRouter()

# Allowed file types and max size
ALLOWED_EXTENSIONS = {".csv", ".json", ".xml", ".nessus", ".sarif", ".pdf", ".zip"}
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/json",
    "text/xml",
    "application/xml",
    "text/plain",  # .nessus files are often text/plain
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",  # For .sarif and unknown types
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))


def _validate_file(file: UploadFile) -> None:
    """Validate file extension, MIME type, and size."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a name"
        )
    
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Validate MIME type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"MIME type '{content_type}' not allowed"
        )


@router.post("/upload", response_model=dict)
async def upload_file(
    principal: WriterDep,
    file: Annotated[UploadFile, File()],
    description: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Upload a vulnerability scan result or report file.
    
    Allowed types: .csv, .json, .xml, .nessus, .sarif, .pdf, .zip
    Max size: 50MB
    """
    _validate_file(file)
    
    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix.lower()
    safe_filename = f"{file_id}{ext}"
    file_path = UPLOAD_DIR / safe_filename
    
    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Audit log
    audit = AuditService(db)
    audit.log(
        user_id=str(principal.id),
        action="FILE_UPLOAD",
        resource_type="upload",
        resource_id=file_id,
        details={
            "original_filename": file.filename,
            "saved_as": safe_filename,
            "size": len(content),
            "description": description,
        }
    )
    
    return {
        "id": file_id,
        "original_filename": file.filename,
        "saved_filename": safe_filename,
        "size": len(content),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "message": "File uploaded successfully"
    }


@router.get("/uploads/{file_id}")
async def download_file(
    file_id: str,
    principal: WriterDep,
) -> FileResponse:
    """Download an uploaded file."""
    # Find file by ID (scan directory)
    for ext in ALLOWED_EXTENSIONS:
        file_path = UPLOAD_DIR / f"{file_id}{ext}"
        if file_path.exists():
            return FileResponse(
                path=file_path,
                filename=file_path.name,
                media_type="application/octet-stream"
            )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found"
    )


@router.delete("/uploads/{file_id}", response_model=dict)
async def delete_file(
    file_id: str,
    principal: AdminDep,
    db: Session = Depends(get_db),
) -> dict:
    """Delete an uploaded file (admin only)."""
    # Find and delete file
    for ext in ALLOWED_EXTENSIONS:
        file_path = UPLOAD_DIR / f"{file_id}{ext}"
        if file_path.exists():
            file_path.unlink()
            
            # Audit log
            audit = AuditService(db)
            audit.log(
                user_id=str(principal.id),
                action="FILE_DELETE",
                resource_type="upload",
                resource_id=file_id,
            )
            
            return {"message": "File deleted successfully"}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="File not found"
    )


@router.get("/uploads", response_model=list[dict])
async def list_uploads(
    principal: WriterDep,
) -> list[dict]:
    """List all uploaded files."""
    uploads = []
    
    if UPLOAD_DIR.exists():
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file() and file_path.suffix in ALLOWED_EXTENSIONS:
                stat = file_path.stat()
                uploads.append({
                    "id": file_path.stem,
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "uploaded_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })
    
    # Sort by upload date (newest first)
    uploads.sort(key=lambda x: x["uploaded_at"], reverse=True)
    return uploads
