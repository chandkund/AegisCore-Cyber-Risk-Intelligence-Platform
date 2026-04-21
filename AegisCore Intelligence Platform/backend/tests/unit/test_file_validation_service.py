"""Unit tests for file validation service."""

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.services.file_validation_service import (
    FileValidationError,
    FileValidationService,
)


class TestExtensionValidation:
    """Test file extension validation."""

    def test_valid_extensions(self):
        """Test valid file extensions pass."""
        valid_files = [
            "report.csv",
            "data.json",
            "scan.xml",
            "nessus.nessus",
            "results.sarif",
            "doc.pdf",
            "archive.zip",
        ]
        for filename in valid_files:
            ext = FileValidationService.validate_extension(filename)
            assert ext == Path(filename).suffix.lower()

    def test_invalid_extensions(self):
        """Test invalid file extensions are rejected."""
        invalid_files = [
            "script.exe",
            "document.docx",
            "image.png",
            "code.py",
            "shell.sh",
        ]
        for filename in invalid_files:
            with pytest.raises(FileValidationError) as exc:
                FileValidationService.validate_extension(filename)
            assert "File type not allowed" in str(exc.value)

    def test_empty_filename(self):
        """Test empty filename is rejected."""
        with pytest.raises(FileValidationError) as exc:
            FileValidationService.validate_extension("")
        assert "File must have a name" in str(exc.value)


class TestMimeTypeDetection:
    """Test MIME type detection from file content."""

    def test_detect_pdf(self):
        """Test PDF magic number detection."""
        content = b"%PDF-1.4\n1 0 obj\n<<...>>"
        mime = FileValidationService.detect_mime_type(content)
        assert mime == "application/pdf"

    def test_detect_zip(self):
        """Test ZIP magic number detection."""
        # Create a minimal zip file
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("test.txt", "content")
        content = buffer.getvalue()
        mime = FileValidationService.detect_mime_type(content)
        assert mime == "application/zip"

    def test_detect_json(self):
        """Test JSON detection."""
        content = b'{"key": "value", "array": [1, 2, 3]}'
        mime = FileValidationService.detect_mime_type(content)
        assert mime == "application/json"

    def test_detect_csv(self):
        """Test CSV detection."""
        content = b"header1,header2,header3\nvalue1,value2,value3\n"
        mime = FileValidationService.detect_mime_type(content)
        assert mime == "text/csv"

    def test_detect_xml(self):
        """Test XML detection."""
        content = b"<?xml version=\"1.0\"?><root><item/></root>"
        mime = FileValidationService.detect_mime_type(content)
        assert mime == "text/xml"

    def test_detect_unknown(self):
        """Test unknown content returns octet-stream."""
        content = b"\x00\x01\x02\x03\x04\x05"
        mime = FileValidationService.detect_mime_type(content)
        assert mime == "application/octet-stream"


class TestSizeValidation:
    """Test file size validation."""

    def test_valid_size(self):
        """Test file under max size passes."""
        content = b"x" * (50 * 1024 * 1024 - 1)  # Just under 50MB
        FileValidationService.validate_size(content)  # Should not raise

    def test_oversized_file(self):
        """Test oversized file raises error."""
        from fastapi import HTTPException

        content = b"x" * (50 * 1024 * 1024 + 1)  # Just over 50MB
        with pytest.raises(HTTPException) as exc:
            FileValidationService.validate_size(content)
        assert exc.value.status_code == 413
        assert "too large" in exc.value.detail.lower()


class TestCSVValidation:
    """Test CSV structure validation."""

    def test_valid_csv_with_required_columns(self):
        """Test CSV with required vulnerability columns passes."""
        csv_content = "cve_id,asset_id,severity,title,description\nCVE-2024-1234,asset-1,HIGH,Test Title,Description\n"
        content = csv_content.encode("utf-8")
        FileValidationService.validate_csv_structure(content)  # Should not raise

    def test_csv_missing_required_columns(self):
        """Test CSV missing required columns is rejected."""
        csv_content = "name,value\ntest,123\n"
        content = csv_content.encode("utf-8")
        with pytest.raises(FileValidationError) as exc:
            FileValidationService.validate_csv_structure(content)
        assert "missing required vulnerability fields" in str(exc.value)

    def test_empty_csv(self):
        """Test empty CSV is rejected."""
        content = b""
        with pytest.raises(FileValidationError) as exc:
            FileValidationService.validate_csv_structure(content)
        assert "no headers" in str(exc.value)

    def test_csv_encoding_error(self):
        """Test invalid encoding is handled."""
        content = b"\xff\xfeinvalid bytes"
        # Should not raise, uses replace error handling
        FileValidationService.validate_csv_structure(content)


class TestJSONValidation:
    """Test JSON structure validation."""

    def test_valid_sarif(self):
        """Test valid SARIF JSON passes."""
        sarif = {
            "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "Test"}}}],
        }
        content = json.dumps(sarif).encode("utf-8")
        FileValidationService.validate_json_structure(content, "sarif")

    def test_invalid_json(self):
        """Test invalid JSON is rejected."""
        content = b'{"invalid json: missing closing brace'
        with pytest.raises(FileValidationError) as exc:
            FileValidationService.validate_json_structure(content)
        assert "Invalid JSON" in str(exc.value)

    def test_sarif_missing_runs(self):
        """Test SARIF without runs array is rejected."""
        sarif = {"version": "2.1.0"}
        content = json.dumps(sarif).encode("utf-8")
        with pytest.raises(FileValidationError) as exc:
            FileValidationService.validate_json_structure(content, "sarif")
        assert "missing 'runs' array" in str(exc.value)


class TestFilenameSanitization:
    """Test filename sanitization."""

    def test_basic_sanitization(self):
        """Test basic filename sanitization."""
        assert FileValidationService.sanitize_filename("test.csv") == "test.csv"

    def test_path_traversal_attempt(self):
        """Test path traversal is prevented."""
        assert FileValidationService.sanitize_filename("../../../etc/passwd") == "passwd"

    def test_special_characters(self):
        """Test special characters are replaced."""
        result = FileValidationService.sanitize_filename("file<name>with:chars.csv")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result

    def test_long_filename(self):
        """Test long filenames are truncated."""
        long_name = "a" * 300 + ".csv"
        result = FileValidationService.sanitize_filename(long_name)
        assert len(result) <= 200

    def test_hidden_file(self):
        """Test hidden files are sanitized."""
        result = FileValidationService.sanitize_filename(".hidden")
        assert not result.startswith(".")


class TestAsyncValidation:
    """Test async upload validation."""

    @pytest.mark.asyncio
    async def test_valid_csv_upload(self):
        """Test valid CSV file upload validation."""
        csv_content = "cve_id,asset_id,severity,title\nCVE-2024-1234,asset-1,HIGH,Test\n"

        # Create mock UploadFile
        class MockUploadFile:
            def __init__(self, content, filename, content_type):
                self.content = content
                self.filename = filename
                self.content_type = content_type

            async def read(self):
                return self.content

        file = MockUploadFile(
            csv_content.encode("utf-8"),
            "report.csv",
            "text/csv",
        )

        content, ext, mime = await FileValidationService.validate_upload(file)
        assert ext == ".csv"
        assert mime == "text/csv"

    @pytest.mark.asyncio
    async def test_invalid_mime_type(self):
        """Test mismatched MIME type and content is rejected."""
        # JSON content with CSV extension
        json_content = '{"key": "value"}'

        class MockUploadFile:
            def __init__(self, content, filename, content_type):
                self.content = content
                self.filename = filename
                self.content_type = content_type

            async def read(self):
                return self.content

        file = MockUploadFile(
            json_content.encode("utf-8"),
            "report.csv",  # Claims to be CSV
            "text/csv",
        )

        with pytest.raises(FileValidationError) as exc:
            await FileValidationService.validate_upload(file)
        assert "content does not match" in str(exc.value).lower()
