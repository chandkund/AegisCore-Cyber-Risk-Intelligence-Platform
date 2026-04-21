"""Integration tests for secure upload endpoints."""

import csv
import io
import json
import zipfile
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestUploadValidation:
    """Test upload validation and security."""

    def test_upload_valid_csv(self, auth_headers):
        """Test uploading valid CSV file."""
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"
        
        files = {
            "file": ("report.csv", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "id" in data
        assert data["mime_type"] == "text/csv"
        assert "hash" in data
        assert data["scan_result"] in ["clean", "disabled"]

    def test_upload_valid_json(self, auth_headers):
        """Test uploading valid JSON file."""
        json_content = json.dumps({"findings": [{"id": "1"}]})
        
        files = {
            "file": ("data.json", io.BytesIO(json_content.encode()), "application/json")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK

    def test_upload_invalid_extension(self, auth_headers):
        """Test uploading file with invalid extension is rejected."""
        files = {
            "file": ("malware.exe", io.BytesIO(b"malicious content"), "application/octet-stream")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "File type not allowed" in response.json()["detail"]

    def test_upload_mismatched_mime_type(self, auth_headers):
        """Test uploading file with mismatched MIME type and content."""
        # JSON content with CSV extension
        json_content = json.dumps({"key": "value"})
        
        files = {
            "file": ("report.csv", io.BytesIO(json_content.encode()), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        # Should reject because content doesn't match declared type
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_oversized_file(self, auth_headers):
        """Test uploading oversized file is rejected."""
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        files = {
            "file": ("large.csv", io.BytesIO(large_content), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_upload_invalid_csv_structure(self, auth_headers):
        """Test uploading CSV with wrong structure is rejected."""
        csv_content = "name,value\ntest,123\n"  # Missing required columns
        
        files = {
            "file": ("bad.csv", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "missing required" in response.json()["detail"].lower()


class TestPathTraversalProtection:
    """Test path traversal attack prevention."""

    def test_upload_with_traversal_in_filename(self, auth_headers):
        """Test path traversal in filename is sanitized."""
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"
        
        files = {
            "file": ("../../../etc/passwd", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        # Should succeed but store in safe location
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Storage path should not contain traversal
        assert "../" not in data["storage_path"]
        assert "etc" not in data["storage_path"]


class TestVirusScanning:
    """Test virus scanning integration."""

    @pytest.mark.skip(reason="Requires ClamAV to be running")
    def test_upload_blocked_for_virus(self, auth_headers):
        """Test EICAR test file is blocked."""
        # EICAR standard antivirus test file content
        eicar_content = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        
        files = {
            "file": ("test.txt", io.BytesIO(eicar_content), "text/plain")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "threat detected" in response.json()["detail"].lower()


class TestTenantIsolation:
    """Test tenant isolation in file storage."""

    def test_files_isolated_by_tenant(self, auth_headers, db_session):
        """Test files from different tenants are isolated."""
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"
        
        # Upload file
        files = {
            "file": ("report.csv", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        file_id = response.json()["id"]
        storage_path = response.json()["storage_path"]
        
        # Verify path contains tenant ID
        from app.db.deps import get_db
        from app.models.oltp import UploadFile
        
        upload = db_session.query(UploadFile).filter(UploadFile.id == file_id).first()
        assert str(upload.tenant_id) in storage_path

    def test_cannot_access_other_tenant_file(self, auth_headers):
        """Test user cannot access file from other tenant."""
        # This would require setting up multi-tenant test scenario
        pass


class TestAuditLogging:
    """Test audit logging for uploads."""

    def test_upload_audit_log_created(self, auth_headers, db_session):
        """Test audit log entry is created for upload."""
        from app.models.oltp import AuditLog
        
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"
        
        files = {
            "file": ("report.csv", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check audit log
        log = db_session.query(AuditLog).filter(
            AuditLog.action == "FILE_UPLOAD"
        ).order_by(AuditLog.created_at.desc()).first()
        
        assert log is not None
        assert log.resource_type == "upload"
        assert "hash" in log.payload
        assert "scan_result" in log.payload


class TestFileRetrieval:
    """Test secure file retrieval."""

    def test_download_own_file(self, auth_headers):
        """Test downloading own uploaded file."""
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"
        
        # Upload first
        files = {
            "file": ("report.csv", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        upload_response = client.post(
            "/api/v1/upload",
            files=files,
            headers=auth_headers,
        )
        
        file_id = upload_response.json()["id"]
        
        # Download
        response = client.get(
            f"/api/v1/uploads/{file_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.content == csv_content.encode()

    def test_download_nonexistent_file(self, auth_headers):
        """Test downloading nonexistent file returns 404."""
        response = client.get(
            f"/api/v1/uploads/{uuid4()}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestFileDeletion:
    """Test secure file deletion."""

    def test_delete_own_file(self, admin_headers):
        """Test admin deleting uploaded file."""
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"
        
        # Upload first
        files = {
            "file": ("report.csv", io.BytesIO(csv_content.encode()), "text/csv")
        }
        
        upload_response = client.post(
            "/api/v1/upload",
            files=files,
            headers=admin_headers,
        )
        
        file_id = upload_response.json()["id"]
        
        # Delete
        response = client.delete(
            f"/api/v1/uploads/{file_id}",
            headers=admin_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify file is gone
        get_response = client.get(
            f"/api/v1/uploads/{file_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


@pytest.fixture
def auth_headers():
    """Create authentication headers for regular user."""
    # This would need to be implemented with actual auth setup
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def admin_headers():
    """Create authentication headers for admin user."""
    return {"Authorization": "Bearer admin-test-token"}


@pytest.fixture
def db_session():
    """Get database session for assertions."""
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
