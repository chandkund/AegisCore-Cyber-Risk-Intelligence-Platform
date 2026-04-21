"""Unit tests for secure storage service."""

import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.services.secure_storage_service import (
    PathTraversalError,
    SecureStorageService,
    StorageError,
)


class TestTenantIdValidation:
    """Test tenant ID validation."""

    def test_valid_uuid(self):
        """Test valid UUID passes."""
        service = SecureStorageService()
        tenant_id = uuid4()
        result = service._validate_tenant_id(tenant_id)
        assert result == str(tenant_id)

    def test_invalid_uuid(self):
        """Test invalid UUID is rejected."""
        service = SecureStorageService()
        with pytest.raises(StorageError) as exc:
            service._validate_tenant_id("not-a-uuid")
        assert "Invalid tenant ID" in str(exc.value)

    def test_string_uuid(self):
        """Test string UUID passes."""
        service = SecureStorageService()
        uuid_str = str(uuid4())
        result = service._validate_tenant_id(uuid_str)
        assert result == uuid_str


class TestFilenameSanitization:
    """Test filename sanitization."""

    def test_basic_filename(self):
        """Test basic filename unchanged."""
        service = SecureStorageService()
        assert service._sanitize_filename("report.csv") == "report.csv"

    def test_path_traversal_in_filename(self):
        """Test path traversal in filename is removed."""
        service = SecureStorageService()
        result = service._sanitize_filename("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_special_characters(self):
        """Test special characters replaced."""
        service = SecureStorageService()
        result = service._sanitize_filename("file<name>:test?.csv")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert "?" not in result

    def test_long_filename(self):
        """Test long filename truncated."""
        service = SecureStorageService()
        long_name = "a" * 500 + ".csv"
        result = service._sanitize_filename(long_name)
        assert len(result) <= 200

    def test_leading_dots(self):
        """Test leading dots removed (hidden files)."""
        service = SecureStorageService()
        result = service._sanitize_filename(".hidden.file.csv")
        assert not result.startswith(".")

    def test_empty_filename(self):
        """Test empty filename handled."""
        service = SecureStorageService()
        result = service._sanitize_filename("")
        assert result == "unnamed"


class TestTenantPathValidation:
    """Test tenant path validation."""

    def test_valid_tenant_path(self, tmp_path):
        """Test valid tenant path generation."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        path = service._get_tenant_path(tenant_id)

        assert path.exists() or path.parent.exists()
        assert str(tenant_id) in str(path)

    def test_path_traversal_in_tenant_id(self, tmp_path):
        """Test path traversal in tenant ID is blocked."""
        service = SecureStorageService(tmp_path)

        # Create a fake UUID that looks like path traversal
        fake_uuid = "../../../etc/" + str(uuid4())

        with pytest.raises(StorageError) as exc:
            service._get_tenant_path(fake_uuid)

        assert "Invalid tenant ID" in str(exc.value)


class TestFileStorage:
    """Test file storage operations."""

    def test_store_file_success(self, tmp_path):
        """Test successful file storage."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"test file content"
        filename = "test.csv"

        abs_path, relative_path, file_hash = service.store_file(
            tenant_id, content, filename
        )

        assert abs_path.exists()
        assert abs_path.read_bytes() == content
        assert tenant_id.hex in relative_path
        assert len(file_hash) == 16  # First 16 chars of SHA256

    def test_store_file_creates_directory(self, tmp_path):
        """Test storage creates tenant directory."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"content"

        service.store_file(tenant_id, content, "file.txt")

        tenant_dir = tmp_path / str(tenant_id)
        assert tenant_dir.exists()

    def test_store_file_permissions(self, tmp_path):
        """Test file permissions are set correctly."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"content"

        abs_path, _, _ = service.store_file(tenant_id, content, "file.txt")

        # Check permissions (640 = owner rw, group r, other none)
        mode = abs_path.stat().st_mode
        assert mode & 0o640 == 0o640

    def test_store_file_unique_names(self, tmp_path):
        """Test same file stored twice gets unique names."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"same content"

        _, rel_path1, _ = service.store_file(tenant_id, content, "file.csv")
        _, rel_path2, _ = service.store_file(tenant_id, content, "file.csv")

        assert rel_path1 != rel_path2

    def test_store_file_path_traversal_attempt(self, tmp_path):
        """Test path traversal in filename is blocked."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"content"

        # Even with malicious filename, it should store safely
        _, rel_path, _ = service.store_file(
            tenant_id, content, "../../../etc/passwd"
        )

        # Should be stored in tenant dir, not /etc
        assert "etc" not in rel_path or str(tenant_id) in rel_path


class TestFileRetrieval:
    """Test file retrieval operations."""

    def test_retrieve_existing_file(self, tmp_path):
        """Test retrieving existing file."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"test content"

        _, rel_path, _ = service.store_file(tenant_id, content, "file.txt")

        retrieved_path = service.retrieve_file(tenant_id, rel_path)

        assert retrieved_path.exists()
        assert retrieved_path.read_bytes() == content

    def test_retrieve_nonexistent_file(self, tmp_path):
        """Test retrieving nonexistent file fails."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        with pytest.raises(StorageError) as exc:
            service.retrieve_file(tenant_id, "nonexistent/file.txt")

        assert "File not found" in str(exc.value)

    def test_retrieve_wrong_tenant(self, tmp_path):
        """Test retrieving file from wrong tenant fails."""
        service = SecureStorageService(tmp_path)
        tenant1 = uuid4()
        tenant2 = uuid4()
        content = b"content"

        _, rel_path, _ = service.store_file(tenant1, content, "file.txt")

        with pytest.raises(StorageError) as exc:
            service.retrieve_file(tenant2, rel_path)

        assert "does not match" in str(exc.value)

    def test_retrieve_path_traversal(self, tmp_path):
        """Test path traversal in retrieval is blocked."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        malicious_path = f"../../../etc/passwd"

        with pytest.raises(PathTraversalError) as exc:
            service.retrieve_file(tenant_id, malicious_path)


class TestFileDeletion:
    """Test file deletion operations."""

    def test_delete_existing_file(self, tmp_path):
        """Test deleting existing file."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()
        content = b"content"

        _, rel_path, _ = service.store_file(tenant_id, content, "file.txt")

        service.delete_file(tenant_id, rel_path)

        # Verify file is gone
        with pytest.raises(StorageError):
            service.retrieve_file(tenant_id, rel_path)

    def test_delete_nonexistent_file(self, tmp_path):
        """Test deleting nonexistent file raises error."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        with pytest.raises(StorageError) as exc:
            service.delete_file(tenant_id, "nonexistent/file.txt")


class TestFileListing:
    """Test file listing operations."""

    def test_list_tenant_files(self, tmp_path):
        """Test listing files for tenant."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        service.store_file(tenant_id, b"content1", "file1.txt")
        service.store_file(tenant_id, b"content2", "file2.txt")

        files = service.list_tenant_files(tenant_id)

        assert len(files) == 2
        assert all("filename" in f for f in files)
        assert all("size" in f for f in files)

    def test_list_empty_tenant(self, tmp_path):
        """Test listing files for tenant with no files."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        files = service.list_tenant_files(tenant_id)

        assert files == []

    def test_list_nonexistent_tenant(self, tmp_path):
        """Test listing files for nonexistent tenant."""
        service = SecureStorageService(tmp_path)
        tenant_id = uuid4()

        files = service.list_tenant_files(tenant_id)

        assert files == []


class TestSingleton:
    """Test storage service singleton."""

    def test_get_storage_service_singleton(self):
        """Test that get_storage_service returns singleton."""
        from app.services.secure_storage_service import get_storage_service

        service1 = get_storage_service()
        service2 = get_storage_service()

        assert service1 is service2

    def test_singleton_is_service_instance(self):
        """Test singleton is correct type."""
        from app.services.secure_storage_service import get_storage_service

        service = get_storage_service()
        assert isinstance(service, SecureStorageService)
