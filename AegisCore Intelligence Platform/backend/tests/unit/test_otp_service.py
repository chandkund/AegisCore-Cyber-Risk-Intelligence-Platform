"""Unit tests for OTP service."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.oltp import EmailVerificationOTP, Organization, User
from app.services.otp_service import (
    OTPAlreadyVerifiedError,
    OTPError,
    OTPExpiredError,
    OTPInvalidError,
    OTPMaxAttemptsError,
    OTPRateLimitError,
    OTPService,
)


@pytest.fixture
def test_user_id(db: Session):
    """Persisted user id (OTP rows require FK to users)."""
    org = Organization(
        id=uuid.uuid4(),
        name="OTP Test Org",
        code=f"otp-{uuid.uuid4().hex[:8]}",
        is_active=True,
        approval_status="approved",
    )
    db.add(org)
    uid = uuid.uuid4()
    db.add(
        User(
            id=uid,
            tenant_id=org.id,
            email="otp_user@test.local",
            hashed_password="hashed",
            full_name="OTP User",
            is_active=True,
            email_verified=False,
        )
    )
    db.commit()
    return uid


@pytest.fixture
def otp_service(db: Session):
    """Create OTP service with test database."""
    return OTPService(db)


class TestOTPGeneration:
    """Test OTP generation functionality."""

    def test_generate_returns_six_digit_code(self, otp_service, test_user_id):
        """Generated OTP should be 6 digits."""
        code = otp_service.generate_and_store(test_user_id)
        assert len(code) == 6
        assert code.isdigit()

    def test_generated_codes_are_unique(self, otp_service, test_user_id, monkeypatch):
        """Multiple generated codes should be different."""
        monkeypatch.setattr(OTPService, "RATE_LIMIT_MINUTES", 0)
        codes = [otp_service.generate_and_store(test_user_id) for _ in range(5)]
        assert len(set(codes)) == len(codes)

    def test_otp_stored_in_database(self, otp_service, test_user_id, db):
        """Generated OTP should be stored in database."""
        code = otp_service.generate_and_store(test_user_id)
        
        stored = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).first()
        
        assert stored is not None
        assert stored.code_hash is not None
        assert stored.code_hash != code  # Should be hashed
        assert stored.is_used is False
        assert stored.attempts == 0

    def test_otp_has_expiry(self, otp_service, test_user_id, db):
        """OTP should have expiration time."""
        otp_service.generate_and_store(test_user_id)
        
        stored = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).first()
        
        assert stored.expires_at is not None
        assert stored.expires_at > datetime.utcnow()
        # Default expiry is 10 minutes
        assert stored.expires_at <= datetime.utcnow() + timedelta(minutes=11)


class TestOTPVerification:
    """Test OTP verification functionality."""

    def test_valid_code_verifies_successfully(self, otp_service, test_user_id, db):
        """Valid OTP code should verify successfully."""
        code = otp_service.generate_and_store(test_user_id)
        result = otp_service.verify(test_user_id, code)
        assert result is True

    def test_verified_otp_marked_as_used(self, otp_service, test_user_id, db):
        """After verification, OTP should be marked as used."""
        code = otp_service.generate_and_store(test_user_id)
        otp_service.verify(test_user_id, code)
        
        stored = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).first()
        
        assert stored.is_used is True

    def test_invalid_code_raises_error(self, otp_service, test_user_id):
        """Invalid OTP code should raise error."""
        otp_service.generate_and_store(test_user_id)
        
        with pytest.raises(OTPInvalidError):
            otp_service.verify(test_user_id, "000000")

    def test_wrong_code_increments_attempts(self, otp_service, test_user_id, db):
        """Wrong code should increment attempt counter."""
        otp_service.generate_and_store(test_user_id)
        
        try:
            otp_service.verify(test_user_id, "000000")
        except OTPInvalidError:
            pass
        
        stored = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).first()
        
        assert stored.attempts == 1

    def test_max_attempts_exceeded_raises_error(self, otp_service, test_user_id):
        """Max attempts exceeded should raise specific error."""
        otp_service.generate_and_store(test_user_id)
        
        # Exhaust attempts
        for i in range(5):
            try:
                otp_service.verify(test_user_id, f"{i:06d}")
            except OTPInvalidError:
                pass
        
        with pytest.raises(OTPMaxAttemptsError):
            otp_service.verify(test_user_id, "000000")

    def test_expired_otp_raises_error(self, otp_service, test_user_id):
        """Expired OTP should raise error."""
        # Generate with very short expiry
        code = otp_service.generate_and_store(test_user_id, expiry_minutes=-1)
        
        with pytest.raises(OTPExpiredError):
            otp_service.verify(test_user_id, code)

    def test_reused_code_fails(self, otp_service, test_user_id):
        """Reused OTP code should fail (after first success, user is verified)."""
        code = otp_service.generate_and_store(test_user_id)
        otp_service.verify(test_user_id, code)

        with pytest.raises(OTPAlreadyVerifiedError):
            otp_service.verify(test_user_id, code)


class TestOTPRateLimiting:
    """Test OTP rate limiting."""

    def test_rate_limit_prevents_spam(self, otp_service, test_user_id):
        """Multiple rapid requests should be rate limited."""
        otp_service.generate_and_store(test_user_id)
        
        with pytest.raises(OTPRateLimitError):
            otp_service.generate_and_store(test_user_id)

    def test_can_resend_after_delay(self, otp_service, test_user_id):
        """After delay, new OTP can be generated."""
        otp_service.generate_and_store(test_user_id)
        
        # Modify creation time to bypass rate limit
        db = otp_service.db
        otp_record = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).first()
        otp_record.created_at = datetime.utcnow() - timedelta(minutes=2)
        db.commit()
        
        # Should not raise error now
        code = otp_service.generate_and_store(test_user_id)
        assert code is not None


class TestOTPResend:
    """Test OTP resend functionality."""

    def test_resend_invalidates_old_otp(self, otp_service, test_user_id, db):
        """Resend should invalidate old OTP."""
        old_code = otp_service.generate_and_store(test_user_id)
        
        # Modify creation time to bypass rate limit
        old_otp = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).first()
        old_otp.created_at = datetime.utcnow() - timedelta(minutes=2)
        db.commit()
        
        new_code = otp_service.resend(test_user_id, "test@example.com")
        
        # Old code should not work
        with pytest.raises(OTPInvalidError):
            otp_service.verify(test_user_id, old_code)
        
        # New code should work
        result = otp_service.verify(test_user_id, new_code)
        assert result is True


class TestVerificationStatus:
    """Test verification status checking."""

    def test_status_for_new_user(self, otp_service, test_user_id):
        """New user should have unverified status."""
        status = otp_service.get_verification_status(test_user_id)
        
        assert status["verified"] is False
        assert status["pending_otp"] is False
        assert status["can_resend"] is True

    def test_status_with_pending_otp(self, otp_service, test_user_id):
        """User with active OTP should show pending."""
        otp_service.generate_and_store(test_user_id)
        
        status = otp_service.get_verification_status(test_user_id)
        
        assert status["pending_otp"] is True
        assert status["can_resend"] is False


class TestOTPAlreadyVerified:
    """Test behavior when email already verified."""

    def test_generate_fails_if_already_verified(self, otp_service, db, test_user_id):
        """Should not generate OTP for verified user."""
        user = db.get(User, test_user_id)
        assert user is not None
        user.email_verified = True
        db.commit()

        with pytest.raises(OTPAlreadyVerifiedError):
            otp_service.generate_and_store(test_user_id)

    def test_verify_fails_if_already_verified(self, otp_service, db, test_user_id):
        """Should not verify if already verified."""
        user = db.get(User, test_user_id)
        assert user is not None
        user.email_verified = True
        db.commit()

        with pytest.raises(OTPAlreadyVerifiedError):
            otp_service.verify(test_user_id, "123456")


class TestOTPCleanup:
    """Test expired OTP cleanup."""

    def test_expired_otps_cleaned_on_new_generation(self, otp_service, test_user_id, db):
        """Expired OTPs should be cleaned up when generating new."""
        # Create expired OTP
        expired_otp = EmailVerificationOTP(
            user_id=test_user_id,
            code_hash="hash",
            expires_at=datetime.utcnow() - timedelta(hours=1),
            attempts=0,
            max_attempts=5,
            is_used=False,
        )
        db.add(expired_otp)
        db.commit()
        
        # Generate new OTP - should cleanup expired
        otp_service._cleanup_expired(test_user_id)
        
        # Expired OTP should be deleted
        count = db.query(EmailVerificationOTP).filter(
            EmailVerificationOTP.user_id == test_user_id
        ).count()
        
        assert count == 0
