"""Unit tests for virus scanning service."""

import socket
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services.virus_scan_service import (
    ScanResult,
    VirusScanReport,
    VirusScanService,
)


class TestVirusScanAvailability:
    """Test ClamAV availability detection."""

    @patch("socket.socket")
    async def test_unix_socket_available(self, mock_socket_class):
        """Test detection of ClamAV via Unix socket."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        service = VirusScanService()
        available = await service._is_available()

        assert available is True
        assert service._connection_type == "unix"

    @patch("socket.socket")
    async def test_tcp_available(self, mock_socket_class):
        """Test detection of ClamAV via TCP."""
        mock_socket = MagicMock()
        # First call (unix) fails, second (tcp) succeeds
        mock_socket_class.side_effect = [Exception("Unix failed"), mock_socket]

        service = VirusScanService()
        available = await service._is_available()

        assert available is True
        assert service._connection_type == "tcp"

    @patch("socket.socket")
    async def test_not_available(self, mock_socket_class):
        """Test when ClamAV is not available."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.error()
        mock_socket_class.return_value = mock_socket

        service = VirusScanService()
        available = await service._is_available()

        assert available is False

    async def test_caches_result(self):
        """Test availability result is cached."""
        service = VirusScanService()
        service._enabled = True

        available = await service._is_available()
        assert available is True


class TestVirusScanBytes:
    """Test scanning bytes for viruses."""

    @patch("socket.socket")
    async def test_clean_file(self, mock_socket_class):
        """Test clean file scan result."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"stream: OK\n"
        mock_socket_class.return_value = mock_socket

        service = VirusScanService()
        service._enabled = True
        service._connection_type = "tcp"

        content = b"clean file content"
        report = await service.scan_bytes(content)

        assert report.result == ScanResult.CLEAN
        assert report.threat_found is None

    @patch("socket.socket")
    async def test_infected_file(self, mock_socket_class):
        """Test infected file detection."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"stream: Eicar-Test-Signature FOUND\n"
        mock_socket_class.return_value = mock_socket

        service = VirusScanService()
        service._enabled = True
        service._connection_type = "tcp"

        content = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        report = await service.scan_bytes(content)

        assert report.result == ScanResult.INFECTED
        assert "Eicar-Test-Signature" in report.threat_found

    @patch("socket.socket")
    async def test_scan_error(self, mock_socket_class):
        """Test scan error handling."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"stream: ERROR Unknown command\n"
        mock_socket_class.return_value = mock_socket

        service = VirusScanService()
        service._enabled = True
        service._connection_type = "tcp"

        report = await service.scan_bytes(b"content")

        assert report.result == ScanResult.ERROR
        assert report.error_message is not None

    async def test_disabled_scan(self):
        """Test scanning when service is disabled."""
        service = VirusScanService()
        service._enabled = False

        report = await service.scan_bytes(b"content")

        assert report.result == ScanResult.DISABLED
        assert "disabled" in report.error_message.lower()

    @patch("socket.socket")
    async def test_scan_timeout(self, mock_socket_class):
        """Test timeout handling."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        mock_socket.connect.side_effect = socket.timeout()

        service = VirusScanService()
        service._enabled = True
        service._connection_type = "tcp"

        report = await service.scan_bytes(b"content")

        assert report.result == ScanResult.TIMEOUT


class TestVirusScanFile:
    """Test scanning files on disk."""

    @patch("socket.socket")
    async def test_scan_file_clean(self, mock_socket_class, tmp_path):
        """Test scanning a clean file."""
        mock_socket = MagicMock()
        mock_socket.recv.return_value = b"/path/to/file: OK\n"
        mock_socket_class.return_value = mock_socket

        service = VirusScanService()
        service._enabled = True
        service._connection_type = "tcp"

        test_file = tmp_path / "test.txt"
        test_file.write_text("clean content")

        report = await service.scan_file(test_file)

        assert report.result == ScanResult.CLEAN


class TestScanReport:
    """Test scan report dataclass."""

    def test_clean_report(self):
        """Test clean scan report."""
        report = VirusScanReport(
            result=ScanResult.CLEAN,
            scan_time_ms=150,
        )
        assert report.result == ScanResult.CLEAN
        assert report.threat_found is None
        assert report.scan_time_ms == 150

    def test_infected_report(self):
        """Test infected scan report."""
        report = VirusScanReport(
            result=ScanResult.INFECTED,
            threat_found="Trojan.Win32.Malware",
            scan_time_ms=250,
        )
        assert report.result == ScanResult.INFECTED
        assert report.threat_found == "Trojan.Win32.Malware"

    def test_error_report(self):
        """Test error scan report."""
        report = VirusScanReport(
            result=ScanResult.ERROR,
            error_message="Connection refused",
        )
        assert report.result == ScanResult.ERROR
        assert report.error_message == "Connection refused"


class TestSingleton:
    """Test service singleton."""

    def test_get_service_singleton(self):
        """Test that get_virus_scan_service returns singleton."""
        from app.services.virus_scan_service import get_virus_scan_service

        service1 = get_virus_scan_service()
        service2 = get_virus_scan_service()

        assert service1 is service2

    def test_singleton_is_service_instance(self):
        """Test singleton is correct type."""
        from app.services.virus_scan_service import get_virus_scan_service

        service = get_virus_scan_service()
        assert isinstance(service, VirusScanService)
