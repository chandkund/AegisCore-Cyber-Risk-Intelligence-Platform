"""Multi-Factor Authentication (MFA) service using TOTP.

Implements TOTP-based MFA compatible with Google Authenticator and similar apps.
"""

from __future__ import annotations

import base64
import io
import os
import secrets
from typing import Optional, Tuple
from urllib.parse import quote

import pyotp
import qrcode
from fastapi import HTTPException, status


class MFAError(HTTPException):
    """MFA-related error."""

    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)


class MFAService:
    """Service for managing TOTP-based multi-factor authentication."""

    # TOTP configuration
    TOTP_ISSUER = os.environ.get("APP_NAME", "AegisCore")
    TOTP_DIGITS = 6
    TOTP_INTERVAL = 30  # seconds
    TOTP_ALGORITHM = "SHA1"

    @classmethod
    def generate_secret(cls) -> str:
        """Generate a new TOTP secret key.
        
        Returns:
            Base32-encoded secret key
        """
        # Generate 160-bit secret (32 chars in base32)
        return pyotp.random_base32()

    @classmethod
    def get_provisioning_uri(
        cls,
        secret: str,
        email: str,
        tenant_name: Optional[str] = None,
    ) -> str:
        """Generate provisioning URI for QR code.
        
        Args:
            secret: TOTP secret key
            email: User email address
            tenant_name: Optional tenant/organization name
            
        Returns:
            otpauth:// provisioning URI
        """
        issuer = cls.TOTP_ISSUER
        if tenant_name:
            issuer = f"{cls.TOTP_ISSUER} ({tenant_name})"
        
        # Create TOTP object
        totp = pyotp.TOTP(
            secret,
            digits=cls.TOTP_DIGITS,
            interval=cls.TOTP_INTERVAL,
            issuer=issuer,
        )
        
        # Generate provisioning URI
        account_name = email
        uri = totp.provisioning_uri(
            name=account_name,
            issuer_name=issuer,
        )
        
        return uri

    @classmethod
    def generate_qr_code(cls, provisioning_uri: str) -> str:
        """Generate QR code as base64 PNG.
        
        Args:
            provisioning_uri: The otpauth:// URI
            
        Returns:
            Base64-encoded PNG image
        """
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"

    @classmethod
    def verify_code(
        cls,
        secret: str,
        code: str,
        valid_window: int = 1,
    ) -> bool:
        """Verify TOTP code.
        
        Args:
            secret: TOTP secret key
            code: Code to verify
            valid_window: Number of intervals before/after current to accept
                         (1 = accept 1 interval before and after = 90s window)
            
        Returns:
            True if code is valid, False otherwise
        """
        if not secret or not code:
            return False
        
        # Remove spaces and ensure 6 digits
        code = code.replace(" ", "").strip()
        if len(code) != cls.TOTP_DIGITS or not code.isdigit():
            return False
        
        # Create TOTP object
        totp = pyotp.TOTP(
            secret,
            digits=cls.TOTP_DIGITS,
            interval=cls.TOTP_INTERVAL,
        )
        
        # Verify with window
        return totp.verify(code, valid_window=valid_window)

    @classmethod
    def generate_backup_codes(cls, count: int = 10) -> Tuple[list[str], list[str]]:
        """Generate backup codes for account recovery.
        
        Args:
            count: Number of backup codes to generate
            
        Returns:
            Tuple of (plain_codes, hashed_codes)
            Store hashed_codes in database, show plain_codes to user once
        """
        import hashlib
        
        plain_codes = []
        hashed_codes = []
        
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()  # 8 chars
            # Format as XXXX-XXXX for readability
            formatted = f"{code[:4]}-{code[4:]}"
            
            plain_codes.append(formatted)
            # Store SHA-256 hash
            hashed = hashlib.sha256(code.encode()).hexdigest()
            hashed_codes.append(hashed)
        
        return plain_codes, hashed_codes

    @classmethod
    def verify_backup_code(cls, code: str, hashed_codes: list[str]) -> Tuple[bool, list[str]]:
        """Verify a backup code.
        
        Args:
            code: Code provided by user
            hashed_codes: List of stored hashed codes
            
        Returns:
            Tuple of (is_valid, remaining_codes)
            If valid, returns updated list with used code removed
        """
        import hashlib
        
        # Normalize code
        normalized = code.replace("-", "").replace(" ", "").upper()
        
        # Check against stored hashes
        for i, hashed in enumerate(hashed_codes):
            if hashlib.sha256(normalized.encode()).hexdigest() == hashed:
                # Remove used code and return
                remaining = hashed_codes[:i] + hashed_codes[i+1:]
                return True, remaining
        
        return False, hashed_codes

    @classmethod
    def setup_mfa(cls, email: str, tenant_name: Optional[str] = None) -> dict:
        """Setup MFA for a user.
        
        Args:
            email: User email
            tenant_name: Optional tenant name for issuer
            
        Returns:
            Dict with secret, qr_code, and backup_codes
        """
        # Generate secret
        secret = cls.generate_secret()
        
        # Generate provisioning URI
        uri = cls.get_provisioning_uri(secret, email, tenant_name)
        
        # Generate QR code
        qr_code = cls.generate_qr_code(uri)
        
        # Generate backup codes
        plain_backup_codes, hashed_backup_codes = cls.generate_backup_codes()
        
        return {
            "secret": secret,
            "qr_code": qr_code,
            "provisioning_uri": uri,
            "backup_codes": plain_backup_codes,  # Show to user once
            "hashed_backup_codes": hashed_backup_codes,  # Store in DB
        }

    @classmethod
    def validate_setup(cls, secret: str, code: str) -> bool:
        """Validate MFA setup by verifying a code.
        
        Args:
            secret: TOTP secret
            code: Code from authenticator app
            
        Returns:
            True if code is valid
        """
        return cls.verify_code(secret, code)


class MFARequiredError(HTTPException):
    """Raised when MFA is required but not provided or invalid."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Multi-factor authentication required",
            headers={"WWW-Authenticate": "MFA"},
        )


class MFAVerificationError(HTTPException):
    """Raised when MFA verification fails."""

    def __init__(self, detail: str = "Invalid MFA code"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
