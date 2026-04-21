"""Email verification OTP service with security best practices.

Features:
- Secure 6-digit OTP generation
- Hashed OTP storage (never store raw OTP)
- Configurable expiry (default 10 minutes)
- Brute force protection (max 5 attempts)
- Rate limiting support
- Automatic cleanup of expired OTPs
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from typing import Final

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.oltp import EmailVerificationOTP, User


class OTPError(Exception):
    """Base OTP error."""
    pass


class OTPExpiredError(OTPError):
    """OTP has expired."""
    pass


class OTPInvalidError(OTPError):
    """OTP is invalid."""
    pass


class OTPMaxAttemptsError(OTPError):
    """Maximum attempts exceeded."""
    pass


class OTPAlreadyVerifiedError(OTPError):
    """Email already verified."""
    pass


class OTPRateLimitError(OTPError):
    """Rate limit exceeded."""
    pass


class OTPService:
    """Service for managing email verification OTPs."""

    # OTP configuration
    OTP_LENGTH: Final[int] = 6
    OTP_EXPIRY_MINUTES: Final[int] = 10
    MAX_ATTEMPTS: Final[int] = 5
    RATE_LIMIT_MINUTES: Final[int] = 1  # Min minutes between resends

    def __init__(self, db: Session):
        """Initialize OTP service.
        
        Args:
            db: Database session
        """
        self.db = db

    def generate_and_store(
        self,
        user_id: uuid.UUID,
        expiry_minutes: int | None = None,
    ) -> str:
        """Generate and store a new OTP.
        
        Args:
            user_id: The user ID to generate OTP for
            expiry_minutes: Optional custom expiry time
            
        Returns:
            The raw OTP code (6 digits) - this is the only time it's available
            
        Raises:
            OTPRateLimitError: If rate limit exceeded
            OTPAlreadyVerifiedError: If email already verified
        """
        user = self.db.get(User, user_id)
        if user and user.email_verified:
            raise OTPAlreadyVerifiedError("Email is already verified")

        # Check rate limiting
        self._check_rate_limit(user_id)

        # Clean up old expired OTPs for this user
        self._cleanup_expired(user_id)

        # Generate 6-digit OTP
        raw_code = self._generate_code()

        # Hash the code for storage (never store raw)
        code_hash = hash_password(raw_code)

        # Calculate expiry
        expiry = datetime.utcnow() + timedelta(
            minutes=expiry_minutes or self.OTP_EXPIRY_MINUTES
        )

        # Store in database
        otp_record = EmailVerificationOTP(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expiry,
            attempts=0,
            max_attempts=self.MAX_ATTEMPTS,
            is_used=False,
        )
        self.db.add(otp_record)
        self.db.commit()

        return raw_code

    async def generate_and_send_email(
        self,
        user_id: uuid.UUID,
        user_email: str,
        expiry_minutes: int | None = None,
    ) -> tuple[str, bool]:
        """Generate OTP and send it via email.
        
        This is the main method to call when you need to send a verification
        code to a user's email address.
        
        Args:
            user_id: The user ID
            user_email: The user's email address (where to send the code)
            expiry_minutes: Optional custom expiry time
            
        Returns:
            Tuple of (raw_code: str, email_sent: bool)
            Note: raw_code is only returned for testing purposes.
            In production, the code is only sent via email.
            
        Raises:
            OTPRateLimitError: If rate limit exceeded
        """
        # Generate and store the OTP
        raw_code = self.generate_and_store(user_id, expiry_minutes)
        
        # Send the OTP via email
        from app.services.email_service import get_email_service
        email_service = get_email_service()
        
        email_sent = await email_service.send_otp_verification_email(
            to_email=user_email,
            otp_code=raw_code,
            expires_in_minutes=expiry_minutes or self.OTP_EXPIRY_MINUTES,
        )
        
        return raw_code, email_sent

    async def resend_email(
        self,
        user_id: uuid.UUID,
        user_email: str,
    ) -> tuple[str, bool]:
        """Resend OTP via email.
        
        Args:
            user_id: The user ID
            user_email: The user's email address
            
        Returns:
            Tuple of (raw_code: str, email_sent: bool)
            
        Raises:
            OTPRateLimitError: If rate limit exceeded
            OTPAlreadyVerifiedError: If email already verified
        """
        # Check if already verified
        user = self.db.get(User, user_id)
        if user and user.email_verified:
            raise OTPAlreadyVerifiedError("Email is already verified")

        # Check rate limiting
        self._check_rate_limit(user_id)

        # Invalidate any existing unused OTPs
        self._invalidate_existing(user_id)

        # Generate new OTP and send via email
        return await self.generate_and_send_email(user_id, user_email)

    def verify(
        self,
        user_id: uuid.UUID,
        raw_code: str,
    ) -> bool:
        """Verify an OTP code.
        
        Args:
            user_id: The user ID
            raw_code: The raw OTP code to verify
            
        Returns:
            True if verified successfully
            
        Raises:
            OTPInvalidError: If code is invalid
            OTPExpiredError: If code has expired
            OTPMaxAttemptsError: If max attempts exceeded
            OTPAlreadyVerifiedError: If email already verified
        """
        # Check if user already verified
        user = self.db.get(User, user_id)
        if user and user.email_verified:
            raise OTPAlreadyVerifiedError("Email is already verified")

        # Get the most recent unused OTP for this user
        otp_record = (
            self.db.query(EmailVerificationOTP)
            .filter(
                EmailVerificationOTP.user_id == user_id,
                EmailVerificationOTP.is_used == False,
            )
            .order_by(EmailVerificationOTP.created_at.desc())
            .first()
        )

        if not otp_record:
            raise OTPInvalidError("Invalid or expired verification code")

        # Check if max attempts exceeded
        if otp_record.attempts >= otp_record.max_attempts:
            raise OTPMaxAttemptsError(
                f"Maximum attempts ({otp_record.max_attempts}) exceeded. Please request a new code."
            )

        # Check if expired
        if datetime.utcnow() > otp_record.expires_at:
            raise OTPExpiredError("Verification code has expired. Please request a new code.")

        # Increment attempts
        otp_record.attempts += 1
        self.db.commit()

        # Verify the code (compare hash)
        if not verify_password(raw_code, otp_record.code_hash):
            remaining = otp_record.max_attempts - otp_record.attempts
            raise OTPInvalidError(
                f"Invalid verification code. {remaining} attempts remaining."
            )

        # Mark as used and verify user
        otp_record.is_used = True
        if user:
            user.email_verified = True
        self.db.commit()

        return True

    def resend(
        self,
        user_id: uuid.UUID,
        user_email: str,
    ) -> str:
        """Resend OTP to user.
        
        Args:
            user_id: The user ID
            user_email: The user's email (for notification)
            
        Returns:
            The new raw OTP code
            
        Raises:
            OTPRateLimitError: If rate limit exceeded
            OTPAlreadyVerifiedError: If email already verified
        """
        # Check if already verified
        user = self.db.get(User, user_id)
        if user and user.email_verified:
            raise OTPAlreadyVerifiedError("Email is already verified")

        # Check rate limiting
        self._check_rate_limit(user_id)

        # Invalidate any existing unused OTPs
        self._invalidate_existing(user_id)

        # Generate new OTP
        return self.generate_and_store(user_id)

    def can_resend(self, user_id: uuid.UUID) -> tuple[bool, int]:
        """Check if user can resend OTP and seconds until they can.
        
        Args:
            user_id: The user ID
            
        Returns:
            Tuple of (can_resend: bool, seconds_remaining: int)
        """
        recent_otp = (
            self.db.query(EmailVerificationOTP)
            .filter(EmailVerificationOTP.user_id == user_id)
            .order_by(EmailVerificationOTP.created_at.desc())
            .first()
        )

        if not recent_otp:
            return True, 0

        min_wait = timedelta(minutes=self.RATE_LIMIT_MINUTES)
        time_since = datetime.utcnow() - recent_otp.created_at

        if time_since >= min_wait:
            return True, 0

        seconds_remaining = int((min_wait - time_since).total_seconds())
        return False, seconds_remaining

    def _generate_code(self) -> str:
        """Generate a secure 6-digit OTP code."""
        # Use random.SystemRandom for cryptographically secure random
        return "".join(
            str(random.SystemRandom().randint(0, 9))
            for _ in range(self.OTP_LENGTH)
        )

    def _check_rate_limit(self, user_id: uuid.UUID) -> None:
        """Check rate limiting for OTP generation."""
        can_send, seconds = self.can_resend(user_id)
        if not can_send:
            minutes = seconds // 60
            remaining = seconds % 60
            raise OTPRateLimitError(
                f"Please wait {minutes}m {remaining}s before requesting a new code."
            )

    def _cleanup_expired(self, user_id: uuid.UUID) -> None:
        """Clean up expired OTPs for a user."""
        expired = (
            self.db.query(EmailVerificationOTP)
            .filter(
                EmailVerificationOTP.user_id == user_id,
                EmailVerificationOTP.expires_at < datetime.utcnow(),
            )
            .all()
        )
        for otp in expired:
            self.db.delete(otp)
        if expired:
            self.db.commit()

    def _invalidate_existing(self, user_id: uuid.UUID) -> None:
        """Invalidate any existing unused OTPs."""
        existing = (
            self.db.query(EmailVerificationOTP)
            .filter(
                EmailVerificationOTP.user_id == user_id,
                EmailVerificationOTP.is_used == False,
            )
            .all()
        )
        for otp in existing:
            otp.is_used = True  # Mark as used (invalidated)
        if existing:
            self.db.commit()

    def get_verification_status(self, user_id: uuid.UUID) -> dict:
        """Get email verification status for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict with verification status and pending OTP info
        """
        user = self.db.get(User, user_id)
        if not user:
            return {"verified": False, "email": None, "pending_otp": False}

        pending_otp = (
            self.db.query(EmailVerificationOTP)
            .filter(
                EmailVerificationOTP.user_id == user_id,
                EmailVerificationOTP.is_used == False,
                EmailVerificationOTP.expires_at > datetime.utcnow(),
            )
            .first()
        )

        can_resend, seconds = self.can_resend(user_id)

        return {
            "verified": user.email_verified,
            "email": user.email,
            "pending_otp": pending_otp is not None,
            "otp_expires_at": pending_otp.expires_at.isoformat() if pending_otp else None,
            "otp_attempts": pending_otp.attempts if pending_otp else 0,
            "otp_max_attempts": pending_otp.max_attempts if pending_otp else self.MAX_ATTEMPTS,
            "can_resend": can_resend,
            "resend_seconds_remaining": seconds,
        }
