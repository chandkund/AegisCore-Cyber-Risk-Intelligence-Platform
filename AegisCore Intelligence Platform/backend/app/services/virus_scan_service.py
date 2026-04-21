"""Virus scanning service using ClamAV."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import struct
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ScanResult(Enum):
    """Virus scan result status."""

    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


@dataclass
class VirusScanReport:
    """Virus scan report."""

    result: ScanResult
    threat_found: Optional[str] = None
    error_message: Optional[str] = None
    scan_time_ms: Optional[int] = None


class VirusScanService:
    """Service for virus scanning using ClamAV."""

    CLAMD_SOCKET = os.environ.get("CLAMD_SOCKET", "/var/run/clamav/clamd.ctl")
    CLAMD_HOST = os.environ.get("CLAMD_HOST", "localhost")
    CLAMD_PORT = int(os.environ.get("CLAMD_PORT", "3310"))
    SCAN_TIMEOUT = int(os.environ.get("SCAN_TIMEOUT", "30"))

    def __init__(self):
        self._enabled = None
        self._connection_type = None

    async def _is_available(self) -> bool:
        """Check if ClamAV is available."""
        if self._enabled is not None:
            return self._enabled

        # Try Unix socket first
        if Path(self.CLAMD_SOCKET).exists():
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(self.CLAMD_SOCKET)
                sock.close()
                self._connection_type = "unix"
                self._enabled = True
                logger.info(f"ClamAV available via Unix socket: {self.CLAMD_SOCKET}")
                return True
            except (socket.error, OSError):
                pass

        # Try TCP
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((self.CLAMD_HOST, self.CLAMD_PORT))
            sock.close()
            self._connection_type = "tcp"
            self._enabled = True
            logger.info(f"ClamAV available via TCP: {self.CLAMD_HOST}:{self.CLAMD_PORT}")
            return True
        except (socket.error, OSError):
            pass

        self._enabled = False
        logger.warning("ClamAV not available - virus scanning disabled")
        return False

    async def _send_command(self, command: bytes) -> bytes:
        """Send command to ClamAV daemon."""
        if self._connection_type == "unix":
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self.SCAN_TIMEOUT)
            sock.connect(self.CLAMD_SOCKET)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.SCAN_TIMEOUT)
            sock.connect((self.CLAMD_HOST, self.CLAMD_PORT))

        try:
            sock.send(command)
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Check if response is complete
                if b"\n" in chunk:
                    break
            return response
        finally:
            sock.close()

    async def scan_bytes(self, content: bytes) -> VirusScanReport:
        """
        Scan file content for viruses.

        Args:
            content: File content as bytes

        Returns:
            VirusScanReport with scan results
        """
        if not await self._is_available():
            return VirusScanReport(
                result=ScanResult.DISABLED,
                error_message="Virus scanning is disabled - ClamAV not available",
            )

        try:
            import time

            start_time = time.time()

            # Use INSTREAM command for scanning bytes
            # Format: n:stream_length\n<stream>
            size = len(content)
            command = b"zINSTREAM\x00"
            size_bytes = struct.pack(b"!I", size)

            if self._connection_type == "unix":
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self.SCAN_TIMEOUT)
                sock.connect(self.CLAMD_SOCKET)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.SCAN_TIMEOUT)
                sock.connect((self.CLAMD_HOST, self.CLAMD_PORT))

            try:
                # Send command
                sock.send(command)
                # Send size (4 bytes, network byte order)
                sock.send(size_bytes)
                # Send content
                sock.send(content)
                # Send terminating zero-size chunk
                sock.send(struct.pack(b"!I", 0))

                # Receive response
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk

            finally:
                sock.close()

            scan_time = int((time.time() - start_time) * 1000)
            response_str = response.decode("utf-8", errors="ignore").strip()

            # Parse response
            # "OK" = clean
            # "FOUND" = infected
            # "ERROR" = error

            if "OK" in response_str:
                return VirusScanReport(
                    result=ScanResult.CLEAN,
                    scan_time_ms=scan_time,
                )
            elif "FOUND" in response_str:
                # Extract threat name
                threat = response_str.split("FOUND")[0].strip()
                return VirusScanReport(
                    result=ScanResult.INFECTED,
                    threat_found=threat,
                    scan_time_ms=scan_time,
                )
            elif "ERROR" in response_str:
                error_msg = response_str.split("ERROR")[0].strip()
                logger.error(f"ClamAV scan error: {error_msg}")
                return VirusScanReport(
                    result=ScanResult.ERROR,
                    error_message=f"Scan error: {error_msg}",
                    scan_time_ms=scan_time,
                )
            else:
                return VirusScanReport(
                    result=ScanResult.ERROR,
                    error_message=f"Unknown response: {response_str}",
                    scan_time_ms=scan_time,
                )

        except socket.timeout:
            logger.error("ClamAV scan timeout")
            return VirusScanReport(
                result=ScanResult.TIMEOUT,
                error_message="Scan timeout exceeded",
            )
        except Exception as e:
            logger.exception("Virus scan error")
            return VirusScanReport(
                result=ScanResult.ERROR,
                error_message=f"Scan failed: {str(e)}",
            )

    async def scan_file(self, file_path: Path) -> VirusScanReport:
        """
        Scan file on disk for viruses.

        Args:
            file_path: Path to file to scan

        Returns:
            VirusScanReport with scan results
        """
        if not await self._is_available():
            return VirusScanReport(
                result=ScanResult.DISABLED,
                error_message="Virus scanning is disabled - ClamAV not available",
            )

        try:
            import struct
            import time

            start_time = time.time()

            # Use SCAN command for file path
            abs_path = str(file_path.absolute())
            command = f"zSCAN {abs_path}\x00".encode()

            if self._connection_type == "unix":
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(self.SCAN_TIMEOUT)
                sock.connect(self.CLAMD_SOCKET)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.SCAN_TIMEOUT)
                sock.connect((self.CLAMD_HOST, self.CLAMD_PORT))

            try:
                sock.send(command)
                response = b""
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk

            finally:
                sock.close()

            scan_time = int((time.time() - start_time) * 1000)
            response_str = response.decode("utf-8", errors="ignore").strip()

            if "OK" in response_str:
                return VirusScanReport(
                    result=ScanResult.CLEAN,
                    scan_time_ms=scan_time,
                )
            elif "FOUND" in response_str:
                threat = response_str.split("FOUND")[0].strip()
                return VirusScanReport(
                    result=ScanResult.INFECTED,
                    threat_found=threat,
                    scan_time_ms=scan_time,
                )
            else:
                return VirusScanReport(
                    result=ScanResult.ERROR,
                    error_message=f"Scan error: {response_str}",
                    scan_time_ms=scan_time,
                )

        except socket.timeout:
            return VirusScanReport(
                result=ScanResult.TIMEOUT,
                error_message="Scan timeout exceeded",
            )
        except Exception as e:
            logger.exception("Virus scan error")
            return VirusScanReport(
                result=ScanResult.ERROR,
                error_message=f"Scan failed: {str(e)}",
            )


# Singleton instance
_virus_scan_service: Optional[VirusScanService] = None


def get_virus_scan_service() -> VirusScanService:
    """Get or create virus scan service singleton."""
    global _virus_scan_service
    if _virus_scan_service is None:
        _virus_scan_service = VirusScanService()
    return _virus_scan_service
