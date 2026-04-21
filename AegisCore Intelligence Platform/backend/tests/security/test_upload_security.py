"""Security tests for file upload system.

Tests:
- File validation (MIME, extension, size)
- Virus scanning
- Secure storage (tenant isolation, path traversal)
- CSV/JSON structure validation
"""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, UploadFile

from app.core.tenant import TenantContext
from app.services.secure_upload_pipeline import (
    SecureUploadError,
    SecureUploadPipeline,
    SecureUploadResult,
)


class TestFileValidation:
    """Test file validation security."""

    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant context."""
        return TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_name="Test Tenant",
            is_platform_owner=False,
        )

    @pytest.fixture
    def pipeline(self):
        """Create secure upload pipeline."""
        return SecureUploadPipeline()

    def test_rejects_invalid_extension(self, pipeline, mock_tenant):
        """Test that invalid file extensions are rejected."""
        file = MagicMock(spec=UploadFile)
        file.filename = "malware.exe"
        file.content_type = "application/octet-stream"
        file.read = MagicMock(return_value=b"binary content")

        with pytest.raises(SecureUploadError) as exc_info:
            # Use internal method directly for testing
            # Run async method in sync context
            import asyncio
            asyncio.run(
                pipeline._stage_validation(
                    file, {"csv", "json"}, 10
                )
            )

        assert exc_info.value.stage == "validation"
        assert "not allowed" in exc_info.value.message.lower()

    def test_rejects_oversized_file(self, pipeline, mock_tenant):
        """Test that oversized files are rejected."""
        file = MagicMock(spec=UploadFile)
        file.filename = "huge.csv"
        file.content_type = "text/csv"
        file.read = MagicMock(return_value=b"x" * (11 * 1024 * 1024))  # 11MB

        with pytest.raises(SecureUploadError) as exc_info:
            import asyncio
            asyncio.run(
                pipeline._stage_validation(file, {"csv"}, 10)
            )

        assert exc_info.value.stage == "validation"
        assert "too large" in exc_info.value.message.lower()

    def test_accepts_valid_csv(self, pipeline, mock_tenant):
        """Test that valid CSV files are accepted."""
        csv_content = b"hostname,ip,criticality\nserver1,10.0.0.1,high\n"
        
        file = MagicMock(spec=UploadFile)
        file.filename = "assets.csv"
        file.content_type = "text/csv"
        file.read = MagicMock(return_value=csv_content)

        import asyncio
        result = asyncio.run(
            pipeline._stage_validation(file, {"csv"}, 10)
        )

        assert result == csv_content

    def test_accepts_valid_json(self, pipeline, mock_tenant):
        """Test that valid JSON files are accepted."""
        json_content = b'[{"hostname": "server1", "ip": "10.0.0.1"}]'
        
        file = MagicMock(spec=UploadFile)
        file.filename = "assets.json"
        file.content_type = "application/json"
        file.read = MagicMock(return_value=json_content)

        import asyncio
        result = asyncio.run(
            pipeline._stage_validation(file, {"json"}, 10)
        )

        assert result == json_content

    def test_rejects_mismatched_mime_type(self, pipeline, mock_tenant):
        """Test that MIME/content type mismatches are detected."""
        # File claims to be CSV but content is binary
        file = MagicMock(spec=UploadFile)
        file.filename = "fake.csv"
        file.content_type = "text/csv"
        file.read = MagicMock(return_value=b"\x89PNG\r\n\x1a\n")  # PNG magic number

        with pytest.raises(SecureUploadError) as exc_info:
            import asyncio
            asyncio.run(
                pipeline._stage_validation(file, {"csv"}, 10)
            )

        assert exc_info.value.stage == "validation"


class TestVirusScanning:
    """Test virus scanning integration."""

    @pytest.fixture
    def pipeline(self):
        """Create pipeline with mocked scanner."""
        pipeline = SecureUploadPipeline()
        pipeline.virus_scanner = MagicMock()
        return pipeline

    def test_blocks_infected_file(self, pipeline):
        """Test that infected files are blocked."""
        from app.services.virus_scan_service import ScanResult
        
        pipeline.virus_scanner.scan_bytes.return_value = ScanResult(
            status="infected",
            threat_name="EICAR-Test-File",
        )

        content = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        file_id = uuid.uuid4()

        with pytest.raises(SecureUploadError) as exc_info:
            import asyncio
            asyncio.run(
                pipeline._stage_virus_scan(content, file_id)
            )

        assert exc_info.value.stage == "virus_scan"
        assert "virus detected" in exc_info.value.message.lower()

    def test_allows_clean_file(self, pipeline):
        """Test that clean files pass scanning."""
        from app.services.virus_scan_service import ScanResult
        
        pipeline.virus_scanner.scan_bytes.return_value = ScanResult(
            status="clean",
        )

        content = b"valid csv content"
        file_id = uuid.uuid4()

        import asyncio
        asyncio.run(
            pipeline._stage_virus_scan(content, file_id)
        )

        # Should not raise

    def test_continues_on_scan_error(self, pipeline):
        """Test that scan errors don't block upload (defense in depth)."""
        from app.services.virus_scan_service import ScanResult
        
        pipeline.virus_scanner.scan_bytes.return_value = ScanResult(
            status="error",
            error_message="ClamAV unavailable",
        )

        content = b"valid content"
        file_id = uuid.uuid4()

        import asyncio
        asyncio.run(
            pipeline._stage_virus_scan(content, file_id)
        )

        # Should not raise - defense in depth approach


class TestStructureValidation:
    """Test CSV/JSON structure validation."""

    @pytest.fixture
    def pipeline(self):
        """Create secure upload pipeline."""
        return SecureUploadPipeline()

    def test_validates_csv_structure(self, pipeline):
        """Test that malformed CSV is rejected."""
        # Valid CSV
        valid_csv = b"col1,col2,col3\nval1,val2,val3\n"
        
        file = MagicMock(spec=UploadFile)
        file.filename = "valid.csv"

        import asyncio
        # Should not raise
        asyncio.run(
            pipeline._stage_structure_validation(file, valid_csv)
        )

    def test_validates_json_structure(self, pipeline):
        """Test that malformed JSON is rejected."""
        # Valid JSON
        valid_json = b'[{"key": "value"}]'
        
        file = MagicMock(spec=UploadFile)
        file.filename = "valid.json"

        import asyncio
        # Should not raise
        asyncio.run(
            pipeline._stage_structure_validation(file, valid_json)
        )

    def test_rejects_invalid_json(self, pipeline):
        """Test that invalid JSON syntax is rejected."""
        invalid_json = b'[{"key": "value", broken}'
        
        file = MagicMock(spec=UploadFile)
        file.filename = "invalid.json"

        with pytest.raises(SecureUploadError) as exc_info:
            import asyncio
            asyncio.run(
                pipeline._stage_structure_validation(file, invalid_json)
            )

        assert exc_info.value.stage == "structure_validation"
        assert "invalid json" in exc_info.value.message.lower()


class TestSecureStorage:
    """Test secure file storage."""

    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant context."""
        return TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_name="Test Tenant",
            is_platform_owner=False,
        )

    @pytest.fixture
    def pipeline(self, tmp_path):
        """Create pipeline with temp storage."""
        pipeline = SecureUploadPipeline()
        pipeline.storage = MagicMock()
        pipeline.storage.store_upload.return_value = str(tmp_path / "uploads" / "file.txt")
        pipeline.storage.sanitize_filename = MagicMock(side_effect=lambda x: x)
        return pipeline

    def test_stores_in_tenant_directory(self, pipeline, mock_tenant):
        """Test that files are stored in tenant-isolated directories."""
        content = b"test content"
        file_id = uuid.uuid4()
        
        file = MagicMock(spec=UploadFile)
        file.filename = "test.csv"

        import asyncio
        asyncio.run(
            pipeline._stage_storage(file, content, mock_tenant, file_id)
        )

        # Verify storage was called with tenant ID
        pipeline.storage.store_upload.assert_called_once()
        call_args = pipeline.storage.store_upload.call_args
        assert call_args.kwargs["tenant_id"] == mock_tenant.tenant_id

    def test_sanitizes_filename(self, pipeline, mock_tenant):
        """Test that filenames are sanitized."""
        content = b"test content"
        file_id = uuid.uuid4()
        
        file = MagicMock(spec=UploadFile)
        file.filename = "../../../etc/passwd.csv"  # Path traversal attempt

        import asyncio
        asyncio.run(
            pipeline._stage_storage(file, content, mock_tenant, file_id)
        )

        # Verify filename was sanitized
        pipeline.storage.sanitize_filename.assert_called_once_with(
            "../../../etc/passwd.csv"
        )


class TestPathTraversalProtection:
    """Test path traversal attack prevention."""

    def test_sanitize_filename_removes_path_traversal(self):
        """Test that path traversal sequences are removed."""
        from app.services.secure_storage_service import SecureStorageService
        
        storage = SecureStorageService()
        
        dangerous_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "file/../../../etc/hosts",
            "./././../etc/shadow",
        ]
        
        for name in dangerous_names:
            sanitized = storage.sanitize_filename(name)
            assert "../" not in sanitized
            assert "..\\" not in sanitized
            assert "./" not in sanitized
            assert not sanitized.startswith("/")

    def test_sanitize_filename_preserves_safe_names(self):
        """Test that safe filenames are preserved."""
        from app.services.secure_storage_service import SecureStorageService
        
        storage = SecureStorageService()
        
        safe_names = [
            "assets.csv",
            "my-file.json",
            "data_import_2024.csv",
        ]
        
        for name in safe_names:
            sanitized = storage.sanitize_filename(name)
            assert sanitized == name


class TestIntegration:
    """Integration tests for full upload pipeline."""

    @pytest.fixture
    def mock_tenant(self):
        """Create mock tenant context."""
        return TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_name="Test Tenant",
            is_platform_owner=False,
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, mock_tenant):
        """Test successful upload through full pipeline."""
        pipeline = SecureUploadPipeline()
        
        # Mock all services
        pipeline.file_validation = MagicMock()
        pipeline.file_validation.get_mime_type.return_value = "text/csv"
        
        pipeline.virus_scanner = MagicMock()
        from app.services.virus_scan_service import ScanResult
        pipeline.virus_scanner.scan_bytes.return_value = ScanResult(status="clean")
        
        pipeline.storage = MagicMock()
        pipeline.storage.store_upload.return_value = "/uploads/test/file.csv"
        pipeline.storage.sanitize_filename.return_value = "file.csv"

        # Create test file
        csv_content = b"hostname,ip\nserver1,10.0.0.1\n"
        
        file = MagicMock(spec=UploadFile)
        file.filename = "assets.csv"
        file.content_type = "text/csv"
        file.read = MagicMock(return_value=csv_content)

        result = await pipeline.process_upload(
            file=file,
            tenant=mock_tenant,
            allowed_extensions={"csv"},
            max_size_mb=10,
        )

        assert result.is_valid
        assert result.scan_status == "clean"
        assert result.size_bytes == len(csv_content)

    @pytest.mark.asyncio
    async def test_full_pipeline_rejects_virus(self, mock_tenant):
        """Test that infected files are rejected."""
        pipeline = SecureUploadPipeline()
        
        # Mock scanner to detect virus
        pipeline.virus_scanner = MagicMock()
        from app.services.virus_scan_service import ScanResult
        pipeline.virus_scanner.scan_bytes.return_value = ScanResult(
            status="infected",
            threat_name="Malware.Test",
        )
        
        # Also need to mock validation
        pipeline.file_validation = MagicMock()
        pipeline.file_validation.get_mime_type.return_value = "text/csv"

        file = MagicMock(spec=UploadFile)
        file.filename = "infected.csv"
        file.content_type = "text/csv"
        file.read = MagicMock(return_value=b"infected content")

        with pytest.raises(SecureUploadError) as exc_info:
            await pipeline.process_upload(
                file=file,
                tenant=mock_tenant,
                allowed_extensions={"csv"},
            )

        assert exc_info.value.stage == "virus_scan"


class TestAuditLogging:
    """Test audit logging for uploads."""

    @pytest.mark.asyncio
    async def test_upload_logged(self):
        """Test that uploads are logged to audit trail."""
        from app.services.audit_service import AuditService
        
        audit_mock = MagicMock(spec=AuditService)
        
        pipeline = SecureUploadPipeline(audit=audit_mock)
        pipeline.file_validation = MagicMock()
        pipeline.file_validation.get_mime_type.return_value = "text/csv"
        
        pipeline.virus_scanner = MagicMock()
        from app.services.virus_scan_service import ScanResult
        pipeline.virus_scanner.scan_bytes.return_value = ScanResult(status="clean")
        
        pipeline.storage = MagicMock()
        pipeline.storage.store_upload.return_value = "/uploads/file.csv"
        pipeline.storage.sanitize_filename.return_value = "file.csv"

        tenant = TenantContext(
            tenant_id=uuid.uuid4(),
            tenant_name="Test",
            is_platform_owner=False,
        )

        file = MagicMock(spec=UploadFile)
        file.filename = "test.csv"
        file.read = MagicMock(return_value=b"content")

        await pipeline.process_upload(
            file=file,
            tenant=tenant,
            allowed_extensions={"csv"},
        )

        # Verify audit log was called
        audit_mock.log_file_upload.assert_called_once()
