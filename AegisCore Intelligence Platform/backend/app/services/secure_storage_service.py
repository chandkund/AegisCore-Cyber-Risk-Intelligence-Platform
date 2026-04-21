"""Secure file storage service with tenant isolation and path traversal protection."""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

logger = logging.getLogger(__name__)

# Base upload directory
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))

# Maximum filename length
MAX_FILENAME_LENGTH = 200

# Allowed characters in safe filename
SAFE_FILENAME_CHARS = re.compile(r"[^a-zA-Z0-9._-]")


class StorageError(Exception):
    """Storage operation error."""

    pass


class PathTraversalError(StorageError):
    """Path traversal attempt detected."""

    pass


class SecureStorageService:
    """Service for secure file storage with tenant isolation."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or UPLOAD_DIR)
        self._ensure_base_dir()

    def _ensure_base_dir(self) -> None:
        """Ensure base directory exists with proper permissions."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # Set permissions to 750 (owner rwx, group rx, other none)
        os.chmod(self.base_dir, 0o750)

    def _validate_tenant_id(self, tenant_id: UUID | str) -> str:
        """Validate and sanitize tenant ID."""
        tenant_str = str(tenant_id)

        # Validate UUID format
        try:
            UUID(tenant_str)
        except ValueError:
            raise StorageError(f"Invalid tenant ID format: {tenant_str}")

        return tenant_str

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and injection.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for storage
        """
        if not filename:
            return "unnamed"

        # Get basename only (remove any path components)
        basename = Path(filename).name

        # Replace dangerous characters
        sanitized = SAFE_FILENAME_CHARS.sub("_", basename)

        # Remove leading dots (hidden files)
        sanitized = sanitized.lstrip(".")

        # Limit length
        if len(sanitized) > MAX_FILENAME_LENGTH:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[: MAX_FILENAME_LENGTH - len(ext)] + ext

        # Ensure we have something left
        if not sanitized or sanitized == "_":
            sanitized = "unnamed"

        return sanitized

    def _get_tenant_path(self, tenant_id: UUID | str) -> Path:
        """Get validated tenant directory path."""
        tenant_str = self._validate_tenant_id(tenant_id)
        tenant_path = self.base_dir / tenant_str

        # Resolve to absolute path and verify it's under base_dir
        try:
            resolved = tenant_path.resolve()
            base_resolved = self.base_dir.resolve()

            # Check for path traversal
            if not str(resolved).startswith(str(base_resolved)):
                raise PathTraversalError(
                    f"Path traversal detected for tenant: {tenant_str}"
                )

            return resolved
        except (OSError, ValueError) as e:
            raise StorageError(f"Invalid path: {e}")

    def _generate_storage_filename(
        self, original_filename: str, content: bytes
    ) -> Tuple[str, str]:
        """
        Generate secure storage filename with hash prefix.

        Returns:
            Tuple of (storage_filename, file_hash)
        """
        # Calculate content hash
        file_hash = hashlib.sha256(content).hexdigest()[:16]

        # Sanitize original filename
        safe_name = self._sanitize_filename(original_filename)

        # Get extension
        ext = Path(safe_name).suffix.lower()

        # Generate storage name: hash_uuid.ext
        storage_name = f"{file_hash}_{uuid.uuid4().hex[:8]}{ext}"

        return storage_name, file_hash

    def store_file(
        self,
        tenant_id: UUID | str,
        content: bytes,
        original_filename: str,
    ) -> Tuple[Path, str, str]:
        """
        Store file securely with tenant isolation.

        Args:
            tenant_id: Tenant UUID
            content: File content bytes
            original_filename: Original filename for reference

        Returns:
            Tuple of (absolute_path, storage_relative_path, file_hash)

        Raises:
            StorageError: If storage operation fails
            PathTraversalError: If path traversal detected
        """
        # Get tenant directory
        tenant_path = self._get_tenant_path(tenant_id)

        # Create tenant directory if needed
        tenant_path.mkdir(parents=True, exist_ok=True)
        os.chmod(tenant_path, 0o750)

        # Generate secure filename
        storage_name, file_hash = self._generate_storage_filename(
            original_filename, content
        )

        # Full file path
        file_path = tenant_path / storage_name

        # Final path traversal check
        try:
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(tenant_path.resolve())):
                raise PathTraversalError("Path traversal in filename detected")
        except (OSError, ValueError) as e:
            raise StorageError(f"Invalid file path: {e}")

        # Write file with proper permissions
        try:
            with open(file_path, "wb") as f:
                f.write(content)

            # Set permissions to 640 (owner rw, group r, other none)
            os.chmod(file_path, 0o640)

            # Calculate relative path for storage
            relative_path = f"{self._validate_tenant_id(tenant_id)}/{storage_name}"

            logger.info(
                f"File stored: {relative_path} "
                f"(tenant={tenant_id}, size={len(content)}, hash={file_hash})"
            )

            return file_path, relative_path, file_hash

        except OSError as e:
            raise StorageError(f"Failed to write file: {e}")

    def retrieve_file(
        self,
        tenant_id: UUID | str,
        storage_path: str,
    ) -> Path:
        """
        Retrieve file path after validation.

        Args:
            tenant_id: Expected tenant UUID
            storage_path: Storage-relative path

        Returns:
            Absolute file path

        Raises:
            StorageError: If file not found or access denied
            PathTraversalError: If path traversal detected
        """
        # Validate storage path components
        tenant_str = self._validate_tenant_id(tenant_id)

        # Parse storage path
        parts = storage_path.replace("\\", "/").split("/")

        # Verify tenant matches
        if len(parts) < 2 or parts[0] != tenant_str:
            raise StorageError("Storage path does not match tenant")

        # Build full path
        file_path = self.base_dir / storage_path

        # Resolve and validate
        try:
            resolved = file_path.resolve()
            tenant_path = self._get_tenant_path(tenant_id)

            # Ensure file is within tenant directory
            if not str(resolved).startswith(str(tenant_path)):
                raise PathTraversalError("File access outside tenant directory")

            # Check file exists
            if not resolved.exists():
                raise StorageError("File not found")

            if not resolved.is_file():
                raise StorageError("Not a regular file")

            return resolved

        except (OSError, ValueError) as e:
            raise StorageError(f"Cannot access file: {e}")

    def delete_file(
        self,
        tenant_id: UUID | str,
        storage_path: str,
    ) -> None:
        """
        Delete file securely.

        Args:
            tenant_id: Expected tenant UUID
            storage_path: Storage-relative path

        Raises:
            StorageError: If deletion fails
        """
        file_path = self.retrieve_file(tenant_id, storage_path)

        try:
            file_path.unlink()
            logger.info(f"File deleted: {storage_path} (tenant={tenant_id})")
        except OSError as e:
            raise StorageError(f"Failed to delete file: {e}")

    def get_file_size(
        self,
        tenant_id: UUID | str,
        storage_path: str,
    ) -> int:
        """Get file size after validation."""
        file_path = self.retrieve_file(tenant_id, storage_path)
        return file_path.stat().st_size

    def list_tenant_files(
        self,
        tenant_id: UUID | str,
    ) -> list[dict]:
        """
        List all files for a tenant.

        Returns:
            List of file metadata dictionaries
        """
        tenant_path = self._get_tenant_path(tenant_id)

        if not tenant_path.exists():
            return []

        files = []
        for file_path in tenant_path.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                })

        return files


# Singleton instance
_storage_service: Optional[SecureStorageService] = None


def get_storage_service() -> SecureStorageService:
    """Get or create storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = SecureStorageService()
    return _storage_service
