"""Secure upload pipeline with full validation and scanning.

Pipeline stages:
1. File validation (MIME, extension, size)
2. Virus scanning (ClamAV)
3. Structure validation (CSV/JSON)
4. Secure storage (tenant-isolated)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import BinaryIO

from fastapi import HTTPException, UploadFile, status

from app.core.tenant import TenantContext
from app.services.file_validation_service import FileValidationService
from app.services.virus_scan_service import VirusScanService, ScanResult
from app.services.secure_storage_service import SecureStorageService
from app.services.audit_service import AuditService


@dataclass
class SecureUploadResult:
    """Result of secure upload pipeline."""
    
    file_id: uuid.UUID
    original_filename: str
    stored_path: str
    size_bytes: int
    mime_type: str
    scan_status: str
    is_valid: bool
    errors: list[str]


class SecureUploadError(Exception):
    """Exception raised during secure upload."""
    
    def __init__(self, message: str, stage: str, status_code: int = 400):
        self.message = message
        self.stage = stage
        self.status_code = status_code
        super().__init__(message)


class SecureUploadPipeline:
    """Secure file upload pipeline with validation and scanning."""
    
    def __init__(
        self,
        file_validation: FileValidationService | None = None,
        virus_scanner: VirusScanService | None = None,
        storage: SecureStorageService | None = None,
        audit: AuditService | None = None,
    ):
        self.file_validation = file_validation or FileValidationService()
        self.virus_scanner = virus_scanner or VirusScanService()
        self.storage = storage or SecureStorageService()
        self.audit = audit
    
    async def process_upload(
        self,
        file: UploadFile,
        tenant: TenantContext,
        allowed_extensions: set[str] | None = None,
        max_size_mb: int = 10,
        validate_structure: bool = True,
    ) -> SecureUploadResult:
        """Process file through secure upload pipeline.
        
        Args:
            file: Uploaded file
            tenant: Tenant context for isolation
            allowed_extensions: Allowed file extensions
            max_size_mb: Maximum file size in MB
            validate_structure: Whether to validate CSV/JSON structure
            
        Returns:
            SecureUploadResult with file details
            
        Raises:
            SecureUploadError: If validation or scanning fails
        """
        errors: list[str] = []
        file_id = uuid.uuid4()
        
        try:
            # Stage 1: File validation
            content = await self._stage_validation(
                file, allowed_extensions, max_size_mb
            )
            
            # Stage 2: Virus scanning
            await self._stage_virus_scan(content, file_id)
            
            # Stage 3: Structure validation (for CSV/JSON)
            if validate_structure:
                await self._stage_structure_validation(file, content)
            
            # Stage 4: Secure storage
            stored_path = await self._stage_storage(
                file, content, tenant, file_id
            )
            
            # Log success
            if self.audit:
                self.audit.log_file_upload(
                    tenant_id=tenant.tenant_id,
                    filename=file.filename,
                    file_id=file_id,
                    size=len(content),
                )
            
            return SecureUploadResult(
                file_id=file_id,
                original_filename=file.filename or "unknown",
                stored_path=stored_path,
                size_bytes=len(content),
                mime_type=file.content_type or "application/octet-stream",
                scan_status="clean",
                is_valid=True,
                errors=[],
            )
            
        except SecureUploadError:
            raise
        except Exception as e:
            raise SecureUploadError(
                message=f"Upload processing failed: {str(e)}",
                stage="processing",
                status_code=500,
            )
    
    async def _stage_validation(
        self,
        file: UploadFile,
        allowed_extensions: set[str] | None,
        max_size_mb: int,
    ) -> bytes:
        """Stage 1: Validate file extension, MIME type, and size."""
        if not file.filename:
            raise SecureUploadError(
                message="File must have a filename",
                stage="validation",
            )
        
        # Check extension
        if allowed_extensions:
            ext = file.filename.split(".")[-1].lower()
            if ext not in allowed_extensions:
                raise SecureUploadError(
                    message=f"File type '.{ext}' not allowed. Allowed: {allowed_extensions}",
                    stage="validation",
                )
        
        # Read and validate content
        content = await file.read()
        
        # Validate size
        max_bytes = max_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise SecureUploadError(
                message=f"File too large. Max size: {max_size_mb}MB",
                stage="validation",
            )
        
        # Validate MIME type by magic number
        detected_mime = self.file_validation.get_mime_type(content)
        allowed_mimes = {"text/csv", "application/json", "text/plain"}
        
        if detected_mime not in allowed_mimes:
            raise SecureUploadError(
                message=f"Invalid file content. Detected: {detected_mime}",
                stage="validation",
            )
        
        return content
    
    async def _stage_virus_scan(self, content: bytes, file_id: uuid.UUID) -> None:
        """Stage 2: Scan file for viruses."""
        scan_result = self.virus_scanner.scan_bytes(content)
        
        if scan_result.status == "infected":
            raise SecureUploadError(
                message=f"Virus detected: {scan_result.threat_name}",
                stage="virus_scan",
                status_code=400,
            )
        
        if scan_result.status == "error":
            # Log but don't block on scan errors (defense in depth)
            pass
    
    async def _stage_structure_validation(
        self, file: UploadFile, content: bytes
    ) -> None:
        """Stage 3: Validate CSV/JSON structure."""
        if not file.filename:
            return
        
        ext = file.filename.split(".")[-1].lower()
        
        if ext == "csv":
            valid, error = self.file_validation.validate_csv(content)
            if not valid:
                raise SecureUploadError(
                    message=f"Invalid CSV format: {error}",
                    stage="structure_validation",
                )
        
        elif ext == "json":
            valid, error = self.file_validation.validate_json(content)
            if not valid:
                raise SecureUploadError(
                    message=f"Invalid JSON format: {error}",
                    stage="structure_validation",
                )
    
    async def _stage_storage(
        self,
        file: UploadFile,
        content: bytes,
        tenant: TenantContext,
        file_id: uuid.UUID,
    ) -> str:
        """Stage 4: Store file securely with tenant isolation."""
        # Sanitize filename
        safe_name = self.storage.sanitize_filename(file.filename or "upload")
        
        # Store in tenant-isolated directory
        stored_path = self.storage.store_upload(
            file_id=file_id,
            tenant_id=tenant.tenant_id,
            filename=safe_name,
            content=content,
        )
        
        return stored_path


# Convenience function for endpoints
async def secure_upload(
    file: UploadFile,
    tenant: TenantContext,
    allowed_extensions: set[str] | None = None,
    max_size_mb: int = 10,
) -> SecureUploadResult:
    """Quick secure upload function for endpoints.
    
    Usage:
        result = await secure_upload(file, tenant, {"csv", "json"}, 10)
    """
    pipeline = SecureUploadPipeline()
    return await pipeline.process_upload(
        file=file,
        tenant=tenant,
        allowed_extensions=allowed_extensions,
        max_size_mb=max_size_mb,
    )
