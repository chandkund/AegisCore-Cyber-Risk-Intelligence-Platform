"""Tests for MFA/TOTP service."""

import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.mfa_service import (
    MFAService,
    MFAError,
    MFARequiredError,
    MFAVerificationError,
)


class TestTOTPSecretGeneration:
    """Test TOTP secret generation."""

    def test_secret_generation(self):
        """Test that secrets are generated correctly."""
        secret = MFAService.generate_secret()
        
        # Should be base32 encoded (A-Z, 2-7)
        assert len(secret) == 32
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)

    def test_secrets_are_unique(self):
        """Test that generated secrets are unique."""
        secrets = [MFAService.generate_secret() for _ in range(10)]
        assert len(set(secrets)) == 10


class TestProvisioningURI:
    """Test provisioning URI generation."""

    def test_provisioning_uri_format(self):
        """Test that provisioning URI has correct format."""
        secret = MFAService.generate_secret()
        uri = MFAService.get_provisioning_uri(secret, "user@example.com")
        
        assert uri.startswith("otpauth://totp/")
        assert "user@example.com" in uri
        assert secret in uri

    def test_provisioning_uri_with_tenant(self):
        """Test that tenant name is included in issuer."""
        secret = MFAService.generate_secret()
        uri = MFAService.get_provisioning_uri(
            secret, "user@example.com", tenant_name="AcmeCorp"
        )
        
        assert "AcmeCorp" in uri


class TestQRCodeGeneration:
    """Test QR code generation."""

    def test_qr_code_generation(self):
        """Test that QR code is generated correctly."""
        secret = MFAService.generate_secret()
        uri = MFAService.get_provisioning_uri(secret, "user@example.com")
        qr_code = MFAService.generate_qr_code(uri)
        
        # Should be base64 PNG
        assert qr_code.startswith("data:image/png;base64,")
        assert len(qr_code) > 100  # Should be substantial


class TestTOTPVerification:
    """Test TOTP code verification."""

    def test_valid_code_verification(self):
        """Test that valid TOTP codes are accepted."""
        import pyotp
        
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        assert MFAService.verify_code(secret, code)

    def test_invalid_code_rejected(self):
        """Test that invalid TOTP codes are rejected."""
        secret = MFAService.generate_secret()
        
        assert not MFAService.verify_code(secret, "000000")

    def test_empty_code_rejected(self):
        """Test that empty codes are rejected."""
        secret = MFAService.generate_secret()
        
        assert not MFAService.verify_code(secret, "")
        assert not MFAService.verify_code(secret, None)

    def test_wrong_length_rejected(self):
        """Test that codes with wrong length are rejected."""
        secret = MFAService.generate_secret()
        
        assert not MFAService.verify_code(secret, "12345")  # Too short
        assert not MFAService.verify_code(secret, "1234567")  # Too long

    def test_non_numeric_rejected(self):
        """Test that non-numeric codes are rejected."""
        secret = MFAService.generate_secret()
        
        assert not MFAService.verify_code(secret, "abcdef")

    def test_code_with_spaces_accepted(self):
        """Test that codes with spaces are normalized."""
        import pyotp
        
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        # Add spaces
        spaced_code = f"{code[:3]} {code[3:]}"
        assert MFAService.verify_code(secret, spaced_code)


class TestTimeWindow:
    """Test TOTP time window validation."""

    def test_code_within_window(self):
        """Test that codes within time window are accepted."""
        import pyotp
        
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        
        # Current code
        code = totp.now()
        assert MFAService.verify_code(secret, code, valid_window=1)

    def test_old_code_rejected_without_window(self):
        """Test that old codes are rejected without window."""
        import pyotp
        
        secret = MFAService.generate_secret()
        totp = pyotp.TOTP(secret)
        
        # Get previous interval code
        old_time = int(time.time()) - 60  # 60 seconds ago
        old_code = totp.at(old_time)
        
        # Should fail without window
        assert not MFAService.verify_code(secret, old_code, valid_window=0)


class TestBackupCodes:
    """Test backup code generation and verification."""

    def test_backup_code_generation(self):
        """Test that backup codes are generated correctly."""
        plain_codes, hashed_codes = MFAService.generate_backup_codes(count=10)
        
        assert len(plain_codes) == 10
        assert len(hashed_codes) == 10
        
        # Plain codes should be formatted
        for code in plain_codes:
            assert len(code) == 9  # XXXX-XXXX
            assert "-" in code

    def test_backup_code_verification(self):
        """Test that backup codes can be verified."""
        plain_codes, hashed_codes = MFAService.generate_backup_codes(count=5)
        
        # Verify first code
        is_valid, remaining = MFAService.verify_backup_code(plain_codes[0], hashed_codes)
        
        assert is_valid
        assert len(remaining) == 4

    def test_backup_code_single_use(self):
        """Test that backup codes can only be used once."""
        plain_codes, hashed_codes = MFAService.generate_backup_codes(count=5)
        
        # Use first code
        is_valid, remaining = MFAService.verify_backup_code(plain_codes[0], hashed_codes)
        assert is_valid
        
        # Try to use same code again
        is_valid, _ = MFAService.verify_backup_code(plain_codes[0], remaining)
        assert not is_valid

    def test_invalid_backup_code(self):
        """Test that invalid backup codes are rejected."""
        plain_codes, hashed_codes = MFAService.generate_backup_codes(count=5)
        
        is_valid, remaining = MFAService.verify_backup_code("INVALID", hashed_codes)
        
        assert not is_valid
        assert len(remaining) == 5  # No codes consumed


class TestMFASetup:
    """Test MFA setup process."""

    def test_setup_returns_all_components(self):
        """Test that setup returns all required components."""
        result = MFAService.setup_mfa("user@example.com")
        
        assert "secret" in result
        assert "qr_code" in result
        assert "provisioning_uri" in result
        assert "backup_codes" in result
        assert "hashed_backup_codes" in result

    def test_setup_validates_correctly(self):
        """Test that setup generates valid configuration."""
        result = MFAService.setup_mfa("user@example.com")
        
        # Should be able to validate a code
        import pyotp
        totp = pyotp.TOTP(result["secret"])
        code = totp.now()
        
        assert MFAService.validate_setup(result["secret"], code)

    def test_setup_with_tenant(self):
        """Test that setup includes tenant name."""
        result = MFAService.setup_mfa("user@example.com", tenant_name="AcmeCorp")
        
        assert "AcmeCorp" in result["provisioning_uri"]


class TestMFAErrors:
    """Test MFA error classes."""

    def test_mfa_required_error(self):
        """Test MFA required error."""
        error = MFARequiredError()
        
        assert error.status_code == 401
        assert "mfa" in error.detail.lower()

    def test_mfa_verification_error(self):
        """Test MFA verification error."""
        error = MFAVerificationError("Custom error message")
        
        assert error.status_code == 401
        assert error.detail == "Custom error message"

    def test_mfa_error_default_message(self):
        """Test MFA verification error with default message."""
        error = MFAVerificationError()
        
        assert "invalid" in error.detail.lower()
