"""Tests for password policy validation."""

import pytest

from app.services.password_policy_service import (
    PasswordPolicyService,
    PasswordValidationError,
)


class TestPasswordLength:
    """Test password length requirements."""

    def test_password_too_short(self):
        """Test that short passwords are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("Short1!")
        assert not is_valid
        assert any("at least 12 characters" in e.lower() for e in errors)

    def test_password_minimum_length(self):
        """Test that 12-character passwords are accepted."""
        is_valid, errors = PasswordPolicyService.validate_password("ValidPass123!")
        assert is_valid
        assert len(errors) == 0

    def test_password_maximum_length(self):
        """Test that very long passwords are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("A" * 129)
        assert not is_valid
        assert any("exceed 128 characters" in e.lower() for e in errors)


class TestPasswordCharacterTypes:
    """Test password character type requirements."""

    def test_missing_uppercase(self):
        """Test that passwords without uppercase are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("lowercase123!")
        assert not is_valid
        assert any("uppercase" in e.lower() for e in errors)

    def test_missing_lowercase(self):
        """Test that passwords without lowercase are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("UPPERCASE123!")
        assert not is_valid
        assert any("lowercase" in e.lower() for e in errors)

    def test_missing_digit(self):
        """Test that passwords without digits are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("NoDigitsHere!!")
        assert not is_valid
        assert any("number" in e.lower() for e in errors)

    def test_missing_special(self):
        """Test that passwords without special chars are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("NoSpecialChars123")
        assert not is_valid
        assert any("special character" in e.lower() for e in errors)

    def test_all_character_types_present(self):
        """Test that valid passwords pass."""
        is_valid, errors = PasswordPolicyService.validate_password("ValidPass123!")
        assert is_valid
        assert len(errors) == 0


class TestCommonPasswords:
    """Test common password detection."""

    def test_common_password_rejected(self):
        """Test that common passwords are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("password123!")
        assert not is_valid
        assert any("too common" in e.lower() for e in errors)

    def test_password123_rejected(self):
        """Test that password123 is rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("Password123!")
        # Should still fail due to common password check
        assert not is_valid or any("common" in e.lower() for e in errors)


class TestPersonalInfo:
    """Test personal information detection."""

    def test_email_in_password(self):
        """Test that passwords containing email are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password(
            "john@example.com123!",
            email="john@example.com"
        )
        assert not is_valid
        assert any("email" in e.lower() for e in errors)

    def test_name_in_password(self):
        """Test that passwords containing name are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password(
            "JohnSmith123!",
            name="John Smith"
        )
        assert not is_valid
        assert any("name" in e.lower() for e in errors)


class TestSequentialPatterns:
    """Test sequential pattern detection."""

    def test_sequential_letters_rejected(self):
        """Test that sequential letters are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("abc123!XYZ#")
        assert not is_valid
        assert any("sequential" in e.lower() for e in errors)

    def test_sequential_numbers_rejected(self):
        """Test that sequential numbers are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("Pass1234!Word")
        assert not is_valid
        assert any("sequential" in e.lower() for e in errors)


class TestRepeatedCharacters:
    """Test repeated character detection."""

    def test_repeated_chars_rejected(self):
        """Test that repeated characters are rejected."""
        is_valid, errors = PasswordPolicyService.validate_password("Paaassword123!")
        assert not is_valid
        assert any("repeated" in e.lower() for e in errors)


class TestStrengthScore:
    """Test password strength scoring."""

    def test_weak_password_score(self):
        """Test that weak passwords have low scores."""
        score = PasswordPolicyService.calculate_strength_score("password")
        assert score < 40

    def test_strong_password_score(self):
        """Test that strong passwords have high scores."""
        score = PasswordPolicyService.calculate_strength_score("MyStr0ng!Pass#2024")
        assert score >= 80

    def test_strength_labels(self):
        """Test strength label generation."""
        assert PasswordPolicyService.get_strength_label(90) == "strong"
        assert PasswordPolicyService.get_strength_label(70) == "moderate"
        assert PasswordPolicyService.get_strength_label(50) == "weak"
        assert PasswordPolicyService.get_strength_label(30) == "very_weak"


class TestPasswordValidationError:
    """Test password validation error raising."""

    def test_validation_error_raises(self):
        """Test that validation error is raised for invalid passwords."""
        with pytest.raises(PasswordValidationError) as exc_info:
            PasswordPolicyService.validate_password_or_raise("short")
        
        assert exc_info.value.status_code == 400
        assert "password" in exc_info.value.detail.lower()

    def test_validation_passes_without_error(self):
        """Test that valid passwords don't raise errors."""
        try:
            PasswordPolicyService.validate_password_or_raise("ValidPass123!")
        except PasswordValidationError:
            pytest.fail("Valid password should not raise error")
