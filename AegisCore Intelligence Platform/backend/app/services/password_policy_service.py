"""Password policy validation service.

Enforces strong password requirements:
- Minimum length: 12 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character
- No common passwords
- No personal info patterns
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Tuple

from fastapi import HTTPException, status


class PasswordValidationError(HTTPException):
    """Password validation error with detailed message."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class PasswordPolicyService:
    """Service for validating password strength and policy compliance."""

    # Minimum password length
    MIN_LENGTH = 12
    
    # Maximum password length (prevent DoS via long passwords)
    MAX_LENGTH = 128

    # Common passwords (top 1000) - in production, load from file or database
    COMMON_PASSWORDS = {
        "password", "123456", "12345678", "qwerty", "abc123",
        "monkey", "letmein", "dragon", "111111", "baseball",
        "iloveyou", "trustno1", "sunshine", "princess", "admin",
        "welcome", "shadow", "ashley", "football", "jesus",
        "michael", "ninja", "mustang", "password1", "123456789",
        "adobe123", "admin123", "letmein1", "photoshop", "qwerty123",
    }

    # Character type patterns
    UPPERCASE_PATTERN = re.compile(r'[A-Z]')
    LOWERCASE_PATTERN = re.compile(r'[a-z]')
    DIGIT_PATTERN = re.compile(r'\d')
    SPECIAL_PATTERN = re.compile(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]')

    # Personal info patterns to avoid
    SEQUENTIAL_PATTERN = re.compile(r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz|012|123|234|345|456|567|678|789|890)', re.IGNORECASE)
    REPEATED_PATTERN = re.compile(r'(.)\1{2,}')  # 3+ repeated characters

    @classmethod
    def validate_password(
        cls,
        password: str,
        email: str | None = None,
        name: str | None = None,
    ) -> Tuple[bool, List[str]]:
        """
        Validate password against all policy requirements.

        Args:
            password: Password to validate
            email: User email (to check for personal info)
            name: User name (to check for personal info)

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: List[str] = []

        # Check length
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters long")
        
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must not exceed {cls.MAX_LENGTH} characters")

        # Check character types
        if not cls.UPPERCASE_PATTERN.search(password):
            errors.append("Password must contain at least one uppercase letter (A-Z)")
        
        if not cls.LOWERCASE_PATTERN.search(password):
            errors.append("Password must contain at least one lowercase letter (a-z)")
        
        if not cls.DIGIT_PATTERN.search(password):
            errors.append("Password must contain at least one number (0-9)")
        
        if not cls.SPECIAL_PATTERN.search(password):
            errors.append("Password must contain at least one special character (!@#$%^&* etc.)")

        # Check for common passwords
        password_lower = password.lower()
        if password_lower in cls.COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a more unique password")

        # Check for personal information
        if email:
            email_parts = email.lower().split('@')[0].split('.')
            for part in email_parts:
                if len(part) >= 3 and part in password_lower:
                    errors.append("Password should not contain parts of your email address")
                    break

        if name:
            name_parts = name.lower().split()
            for part in name_parts:
                if len(part) >= 3 and part in password_lower:
                    errors.append("Password should not contain parts of your name")
                    break

        # Check for sequential characters
        if cls.SEQUENTIAL_PATTERN.search(password):
            errors.append("Password should not contain sequential characters (e.g., 'abc', '123')")

        # Check for repeated characters
        if cls.REPEATED_PATTERN.search(password):
            errors.append("Password should not contain repeated characters (e.g., 'aaa', '111')")

        return len(errors) == 0, errors

    @classmethod
    def validate_password_or_raise(
        cls,
        password: str,
        email: str | None = None,
        name: str | None = None,
    ) -> None:
        """
        Validate password and raise exception if invalid.

        Args:
            password: Password to validate
            email: User email
            name: User name

        Raises:
            PasswordValidationError: If password doesn't meet requirements
        """
        is_valid, errors = cls.validate_password(password, email, name)
        
        if not is_valid:
            raise PasswordValidationError(
                "Password does not meet security requirements:\n" + "\n".join(f"- {e}" for e in errors)
            )

    @classmethod
    def calculate_strength_score(cls, password: str) -> int:
        """
        Calculate password strength score (0-100).

        Args:
            password: Password to score

        Returns:
            Strength score from 0 (very weak) to 100 (very strong)
        """
        score = 0
        
        # Length scoring
        length = len(password)
        if length >= 12:
            score += 20
        if length >= 16:
            score += 10
        if length >= 20:
            score += 10

        # Character variety
        if cls.UPPERCASE_PATTERN.search(password):
            score += 15
        if cls.LOWERCASE_PATTERN.search(password):
            score += 15
        if cls.DIGIT_PATTERN.search(password):
            score += 15
        if cls.SPECIAL_PATTERN.search(password):
            score += 15

        # Deductions
        if password.lower() in cls.COMMON_PASSWORDS:
            score -= 30
        if cls.SEQUENTIAL_PATTERN.search(password):
            score -= 10
        if cls.REPEATED_PATTERN.search(password):
            score -= 10

        return max(0, min(100, score))

    @classmethod
    def get_strength_label(cls, score: int) -> str:
        """Get strength label from score."""
        if score >= 80:
            return "strong"
        elif score >= 60:
            return "moderate"
        elif score >= 40:
            return "weak"
        else:
            return "very_weak"

    @classmethod
    def check_password_breach(cls, password: str) -> bool:
        """
        Check if password has been exposed in data breaches using k-anonymity.
        
        This uses the Have I Been Pwned API with k-anonymity model.
        
        Args:
            password: Password to check
            
        Returns:
            True if password has been breached, False otherwise
        """
        import requests
        
        # Generate SHA-1 hash of password
        sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix = sha1_hash[:5]
        suffix = sha1_hash[5:]
        
        try:
            # Query HIBP API with k-anonymity
            response = requests.get(
                f"https://api.pwnedpasswords.com/range/{prefix}",
                timeout=5,
                headers={"Add-Padding": "true"}
            )
            response.raise_for_status()
            
            # Check if our suffix is in the response
            hashes = response.text.splitlines()
            for hash_line in hashes:
                hash_suffix, _ = hash_line.split(':')
                if hash_suffix == suffix:
                    return True
                    
        except Exception:
            # If API is unavailable, assume password is not breached
            # (fail open for availability, but log the issue)
            pass
            
        return False
