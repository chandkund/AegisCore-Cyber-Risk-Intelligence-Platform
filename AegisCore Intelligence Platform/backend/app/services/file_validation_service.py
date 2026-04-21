"""Secure file validation service with MIME sniffing and content validation."""

from __future__ import annotations

import csv
import io
import json
import mimetypes
import re
import struct
from pathlib import Path
from typing import BinaryIO, Set

from fastapi import HTTPException, UploadFile, status

# Magic numbers for file type detection
MAGIC_NUMBERS = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/zip",
    b"PK\x05\x06": "application/zip",
    b"PK\x07\x08": "application/zip",
    b"<?xml": "text/xml",
    b"<nessus": "text/xml",  # Nessus files are XML
}

# Allowed file extensions and their expected MIME types
ALLOWED_EXTENSIONS = {
    ".csv": {"text/csv", "application/csv", "text/plain"},
    ".json": {"application/json", "text/json", "text/plain"},
    ".xml": {"text/xml", "application/xml", "text/plain"},
    ".nessus": {"text/xml", "application/xml", "text/plain"},
    ".sarif": {"application/json", "text/json", "text/plain"},
    ".pdf": {"application/pdf"},
    ".zip": {"application/zip", "application/x-zip-compressed", "application/octet-stream"},
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# CSV required columns for vulnerability reports
REQUIRED_CSV_COLUMNS = {
    "cve_id",
    "asset_id",
    "severity",
    "title",
}

# JSON schema for SARIF files
SARIF_SCHEMA = {
    "type": "object",
    "required": ["version", "runs"],
    "properties": {
        "version": {"type": "string"},
        "runs": {"type": "array"},
    },
}


class FileValidationError(HTTPException):
    """Custom exception for file validation errors."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class FileValidationService:
    """Service for secure file validation."""

    @staticmethod
    def detect_mime_type(content: bytes) -> str:
        """Detect MIME type from file content using magic numbers."""
        # Check magic numbers
        for magic, mime_type in MAGIC_NUMBERS.items():
            if content.startswith(magic):
                return mime_type

        # Check for JSON
        try:
            content_str = content[:1024].decode("utf-8", errors="ignore").strip()
            if content_str.startswith("{") or content_str.startswith("["):
                # Try to parse as JSON
                json.loads(content_str[:256])
                return "application/json"
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        # Check for CSV
        try:
            content_str = content[:2048].decode("utf-8", errors="ignore")
            if "," in content_str and "\n" in content_str:
                # Try to parse as CSV
                reader = csv.reader(io.StringIO(content_str))
                next(reader)  # Try to read first row
                return "text/csv"
        except (csv.Error, StopIteration):
            pass

        # Check for XML
        try:
            content_str = content[:1024].decode("utf-8", errors="ignore").strip()
            if content_str.startswith("<") and ">" in content_str:
                return "text/xml"
        except UnicodeDecodeError:
            pass

        return "application/octet-stream"

    @staticmethod
    def validate_extension(filename: str) -> str:
        """Validate file extension and return it."""
        if not filename:
            raise FileValidationError("File must have a name")

        ext = Path(filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS.keys())}"
            )

        return ext

    @staticmethod
    def validate_mime_type(ext: str, declared_mime: str, actual_mime: str) -> None:
        """Validate MIME type matches extension and is allowed."""
        allowed_mimes = ALLOWED_EXTENSIONS.get(ext, set())

        # Check if actual MIME type is allowed for this extension
        if actual_mime not in allowed_mimes and declared_mime not in allowed_mimes:
            # Allow some flexibility for text/plain as many scanners use it
            if actual_mime == "application/octet-stream" and "text/plain" in allowed_mimes:
                return
            if actual_mime == "text/plain" and "text/plain" in allowed_mimes:
                return

            raise FileValidationError(
                f"File content does not match declared type. "
                f"Extension '{ext}' expects one of: {', '.join(allowed_mimes)}, "
                f"but detected: {actual_mime}"
            )

    @staticmethod
    def validate_size(content: bytes) -> None:
        """Validate file size."""
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB",
            )

    @staticmethod
    def validate_csv_structure(content: bytes) -> None:
        """Validate CSV file has required columns for vulnerability data."""
        try:
            content_str = content.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(content_str))

            if not reader.fieldnames:
                raise FileValidationError("CSV file has no headers")

            headers = set(reader.fieldnames)

            # Check for at least some required columns (be lenient)
            common_fields = headers & REQUIRED_CSV_COLUMNS
            if len(common_fields) < 2:
                raise FileValidationError(
                    f"CSV missing required vulnerability fields. "
                    f"Found: {', '.join(headers)}, "
                    f"Expected at least 2 of: {', '.join(REQUIRED_CSV_COLUMNS)}"
                )

            # Validate first few rows can be parsed
            for i, row in enumerate(reader):
                if i >= 5:  # Only check first 5 rows
                    break
                if not any(row.values()):
                    raise FileValidationError(f"Empty row found at line {i + 2}")

        except UnicodeDecodeError as e:
            raise FileValidationError(f"CSV file encoding error: {str(e)}")
        except csv.Error as e:
            raise FileValidationError(f"Invalid CSV format: {str(e)}")

    @staticmethod
    def validate_json_structure(content: bytes, schema_type: str = "auto") -> None:
        """Validate JSON file structure."""
        try:
            data = json.loads(content.decode("utf-8", errors="replace"))

            if schema_type == "sarif" or (
                schema_type == "auto" and isinstance(data, dict) and "runs" in data
            ):
                # Validate SARIF structure
                if not isinstance(data.get("runs"), list):
                    raise FileValidationError("SARIF file missing 'runs' array")

            elif schema_type == "nessus" or (
                schema_type == "auto" and isinstance(data, dict) and "Policy" in data
            ):
                # Basic Nessus JSON validation
                pass

        except json.JSONDecodeError as e:
            raise FileValidationError(f"Invalid JSON format: {str(e)}")
        except UnicodeDecodeError as e:
            raise FileValidationError(f"JSON file encoding error: {str(e)}")

    @classmethod
    async def validate_upload(
        cls,
        file: UploadFile,
        validate_structure: bool = True,
    ) -> tuple[bytes, str, str]:
        """
        Comprehensive file validation.

        Returns:
            Tuple of (file_content, extension, detected_mime_type)

        Raises:
            FileValidationError: If validation fails
        """
        # Validate extension first
        ext = cls.validate_extension(file.filename or "")

        # Read content
        content = await file.read()

        # Validate size
        cls.validate_size(content)

        # Detect actual MIME type from content
        actual_mime = cls.detect_mime_type(content)
        declared_mime = file.content_type or "application/octet-stream"

        # Validate MIME type matches extension
        cls.validate_mime_type(ext, declared_mime, actual_mime)

        # Structure validation based on file type
        if validate_structure:
            if ext == ".csv":
                cls.validate_csv_structure(content)
            elif ext in (".json", ".sarif"):
                schema_type = "sarif" if ext == ".sarif" else "auto"
                cls.validate_json_structure(content, schema_type)

        return content, ext, actual_mime

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal and injection."""
        if not filename:
            return "unknown"

        # Remove any path components
        basename = Path(filename).name

        # Remove any non-alphanumeric characters except safe ones
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", basename)

        # Limit length
        if len(sanitized) > 100:
            name, ext = Path(sanitized).stem, Path(sanitized).suffix
            sanitized = name[:90] + ext

        return sanitized or "unknown"
