"""Password validation and strength checking service.

Provides production-grade password validation with:
- Real-time strength scoring (weak/medium/strong)
- Configurable complexity rules
- Common password checking
- Backend and frontend compatible logic
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Final


class PasswordStrength(Enum):
    """Password strength levels."""
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


@dataclass(frozen=True)
class PasswordValidationResult:
    """Result of password validation."""
    is_valid: bool
    strength: PasswordStrength
    score: int  # 0-100
    errors: list[str]
    suggestions: list[str]


class PasswordValidationService:
    """Service for validating password strength and complexity."""

    # Common passwords to block (top 1000 common passwords subset)
    COMMON_PASSWORDS: Final[frozenset[str]] = frozenset({
        "password", "123456", "12345678", "qwerty", "abc123",
        "monkey", "letmein", "dragon", "111111", "baseball",
        "iloveyou", "trustno1", "sunshine", "princess", "admin",
        "welcome", "shadow", "ashley", "football", "jesus",
        "michael", "ninja", "mustang", "password1", "123456789",
        "adobe123", "admin123", "login", "master", "photoshop",
        "qazwsx", "qwertyuiop", "qwerty123", "zaq12wsx", "password123", "root",
    })

    # Minimum requirements
    MIN_LENGTH: Final[int] = 8
    MAX_LENGTH: Final[int] = 128

    @classmethod
    def validate(
        cls,
        password: str,
        user_email: str | None = None,
        user_name: str | None = None,
    ) -> PasswordValidationResult:
        """Validate password and return detailed result.
        
        Args:
            password: The password to validate
            user_email: User's email to check against password
            user_name: User's name to check against password
            
        Returns:
            PasswordValidationResult with validation details
        """
        errors: list[str] = []
        suggestions: list[str] = []
        score = 0

        # Check length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        elif len(password) >= 12:
            score += 25
        elif len(password) >= cls.MIN_LENGTH:
            score += 15

        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must not exceed {cls.MAX_LENGTH} characters")

        # Check for common passwords
        if password.lower() in cls.COMMON_PASSWORDS:
            errors.append("This password is too common and easily guessed")
            score = 0

        # Check for sequential characters
        if cls._has_sequential(password):
            errors.append("Password contains sequential characters (e.g., 'abc', '123')")
            suggestions.append("Avoid using sequential letters or numbers")

        # Check for repeated characters
        if cls._has_repeated_chars(password):
            errors.append("Password contains too many repeated characters")
            suggestions.append("Avoid repeating the same character multiple times")

        # Check complexity - award points for each category
        has_lower = bool(re.search(r"[a-z]", password))
        has_upper = bool(re.search(r"[A-Z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", password))

        complexity_score = sum([has_lower, has_upper, has_digit, has_special]) * 10
        score += complexity_score

        if not has_lower:
            suggestions.append("Add lowercase letters (a-z)")
        if not has_upper:
            suggestions.append("Add uppercase letters (A-Z)")
        if not has_digit:
            suggestions.append("Add numbers (0-9)")
        if not has_special:
            suggestions.append("Add special characters (!@#$%^&*)")

        # Check against user info
        if user_email and cls._contains_user_info(password, user_email):
            errors.append("Password should not contain your email address")
            score -= 20

        if user_name and cls._contains_user_info(password, user_name):
            errors.append("Password should not contain your name")
            score -= 20

        # Determine strength (60+ allows strong passwords with max complexity score 65)
        if score >= 60 and len(password) >= 12 and complexity_score >= 30:
            strength = PasswordStrength.STRONG
        elif score >= 40 and len(password) >= 8 and complexity_score >= 20:
            strength = PasswordStrength.MEDIUM
        else:
            strength = PasswordStrength.WEAK

        # Cap score
        score = max(0, min(100, score))

        is_valid = (
            len(errors) == 0
            and strength in (PasswordStrength.MEDIUM, PasswordStrength.STRONG)
            and len(password) >= cls.MIN_LENGTH
        )

        return PasswordValidationResult(
            is_valid=is_valid,
            strength=strength,
            score=score,
            errors=errors,
            suggestions=suggestions if not is_valid else [],
        )

    @classmethod
    def get_strength_label(cls, strength: PasswordStrength) -> str:
        """Get human-readable strength label."""
        labels = {
            PasswordStrength.WEAK: "Weak",
            PasswordStrength.MEDIUM: "Medium",
            PasswordStrength.STRONG: "Strong",
        }
        return labels[strength]

    @classmethod
    def get_strength_color(cls, strength: PasswordStrength) -> str:
        """Get color code for strength level."""
        colors = {
            PasswordStrength.WEAK: "#ef4444",  # red-500
            PasswordStrength.MEDIUM: "#f59e0b",  # amber-500
            PasswordStrength.STRONG: "#22c55e",  # green-500
        }
        return colors[strength]

    @staticmethod
    def _has_sequential(password: str) -> bool:
        """Check for sequential characters."""
        # Check for 3+ sequential digits
        if re.search(r"(?:012|123|234|345|456|567|678|789|890)", password):
            return True
        # Check for 3+ sequential letters
        password_lower = password.lower()
        for i in range(len(password_lower) - 2):
            c1, c2, c3 = password_lower[i], password_lower[i + 1], password_lower[i + 2]
            if c1.isalpha() and c2.isalpha() and c3.isalpha():
                if ord(c2) == ord(c1) + 1 and ord(c3) == ord(c2) + 1:
                    return True
        return False

    @staticmethod
    def _has_repeated_chars(password: str) -> bool:
        """Check for excessive repeated characters."""
        # Check for 3+ same characters in a row
        return bool(re.search(r"(.)\1{2,}", password))

    @staticmethod
    def _contains_user_info(password: str, user_info: str) -> bool:
        """Check if password contains user info."""
        if not user_info:
            return False
        # Check various parts of email/name
        parts = user_info.lower().split("@")[0].split(".")  # email local part
        parts.extend(user_info.lower().split())  # name parts
        password_lower = password.lower()
        return any(len(part) >= 3 and part in password_lower for part in parts)


def validate_password_strength(
    password: str,
    user_email: str | None = None,
    user_name: str | None = None,
) -> dict:
    """Convenience function for API responses.
    
    Returns a dictionary with validation results suitable for JSON serialization.
    """
    result = PasswordValidationService.validate(password, user_email, user_name)
    return {
        "is_valid": result.is_valid,
        "strength": result.strength.value,
        "score": result.score,
        "errors": result.errors,
        "suggestions": result.suggestions,
        "label": PasswordValidationService.get_strength_label(result.strength),
        "color": PasswordValidationService.get_strength_color(result.strength),
        "min_length": PasswordValidationService.MIN_LENGTH,
        "max_length": PasswordValidationService.MAX_LENGTH,
    }
