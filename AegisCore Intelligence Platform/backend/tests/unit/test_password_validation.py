"""Unit tests for password validation service."""

import pytest

from app.services.password_validation_service import (
    PasswordStrength,
    PasswordValidationService,
    validate_password_strength,
)


class TestPasswordValidationService:
    """Test password validation logic."""

    def test_empty_password_fails(self):
        """Empty password should fail validation."""
        result = PasswordValidationService.validate("")
        assert not result.is_valid
        assert result.score < 40
        assert PasswordStrength.WEAK == result.strength

    def test_short_password_fails(self):
        """Short password should fail validation."""
        result = PasswordValidationService.validate("short")
        assert not result.is_valid
        assert "Password must be at least 8 characters" in result.errors

    def test_password_without_uppercase(self):
        """Password without uppercase gets suggestion."""
        result = PasswordValidationService.validate("lowercase123!")
        assert any("uppercase" in s.lower() for s in result.suggestions)

    def test_password_without_lowercase(self):
        """Password without lowercase gets suggestion."""
        result = PasswordValidationService.validate("UPPERCASE123!")
        assert any("lowercase" in s.lower() for s in result.suggestions)

    def test_password_without_numbers(self):
        """Password without numbers gets suggestion (invalid password so suggestions are kept)."""
        result = PasswordValidationService.validate("AbCdEf!")
        assert any("number" in s.lower() or "digit" in s.lower() for s in result.suggestions)

    def test_password_without_special_chars(self):
        """Password without special chars gets suggestion."""
        result = PasswordValidationService.validate("NoSpecialChars123")
        assert any("special" in s.lower() for s in result.suggestions)

    def test_common_password_rejected(self):
        """Common passwords should be rejected."""
        common_passwords = ["password", "12345678", "qwerty123", "admin123"]
        for pwd in common_passwords:
            result = PasswordValidationService.validate(pwd)
            assert not result.is_valid
            assert any("common" in e.lower() for e in result.errors)

    def test_sequential_chars_rejected(self):
        """Sequential characters should be detected."""
        result = PasswordValidationService.validate("abc123!@#ABC")
        assert any("sequential" in e.lower() for e in result.errors)

    def test_repeated_chars_rejected(self):
        """Repeated characters should be detected."""
        result = PasswordValidationService.validate("aaaAAA111!!!")
        assert any("repeated" in e.lower() for e in result.errors)

    def test_password_with_user_email_rejected(self):
        """Password containing email should be rejected."""
        result = PasswordValidationService.validate(
            "user@example.com123!",
            user_email="user@example.com"
        )
        assert any("email" in e.lower() for e in result.errors)

    def test_password_with_user_name_rejected(self):
        """Password containing user name should be rejected."""
        result = PasswordValidationService.validate(
            "JohnDoe123!",
            user_name="John Doe"
        )
        assert any("name" in e.lower() for e in result.errors)

    def test_strong_password_passes(self):
        """Strong password should pass validation."""
        result = PasswordValidationService.validate("Tr0ub4dor&3x!Complex")
        assert result.is_valid
        assert result.strength == PasswordStrength.STRONG
        assert result.score >= 60

    def test_medium_password_passes(self):
        """Medium strength password should pass."""
        result = PasswordValidationService.validate("GoodP@ss1")
        assert result.is_valid
        assert result.strength == PasswordStrength.MEDIUM

    def test_get_strength_label(self):
        """Test strength label mapping."""
        assert PasswordValidationService.get_strength_label(PasswordStrength.WEAK) == "Weak"
        assert PasswordValidationService.get_strength_label(PasswordStrength.MEDIUM) == "Medium"
        assert PasswordValidationService.get_strength_label(PasswordStrength.STRONG) == "Strong"

    def test_get_strength_color(self):
        """Test strength color mapping."""
        assert PasswordValidationService.get_strength_color(PasswordStrength.WEAK) == "#ef4444"
        assert PasswordValidationService.get_strength_color(PasswordStrength.MEDIUM) == "#f59e0b"
        assert PasswordValidationService.get_strength_color(PasswordStrength.STRONG) == "#22c55e"


class TestValidatePasswordStrengthAPI:
    """Test the API response function."""

    def test_returns_dict_with_required_fields(self):
        """API response should include all required fields."""
        result = validate_password_strength("Test@123")
        
        required_fields = [
            "is_valid", "strength", "score", "errors", 
            "suggestions", "label", "color", "min_length", "max_length"
        ]
        for field in required_fields:
            assert field in result

    def test_max_length_enforced(self):
        """Password exceeding max length should be flagged."""
        long_password = "a" * 200
        result = validate_password_strength(long_password)
        assert any("128" in e for e in result["errors"])


class TestPasswordEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_exactly_min_length_password(self):
        """Password at exactly minimum length."""
        pwd = "A1!" + "a" * 5  # 8 characters total
        result = PasswordValidationService.validate(pwd)
        assert len(pwd) == PasswordValidationService.MIN_LENGTH

    def test_unicode_characters(self):
        """Password with unicode characters."""
        result = PasswordValidationService.validate("Test123!日本語")
        # Should handle unicode without crashing
        assert isinstance(result.score, int)

    def test_whitespace_only_password(self):
        """Password with only whitespace."""
        result = PasswordValidationService.validate("   ")
        assert not result.is_valid

    def test_null_bytes_rejected(self):
        """Password with null bytes should be handled."""
        result = PasswordValidationService.validate("Test\x00Password123!")
        # Should not crash
        assert isinstance(result.errors, list)
