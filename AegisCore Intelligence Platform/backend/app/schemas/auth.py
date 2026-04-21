from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
import re

EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class LoginRequest(BaseModel):
    company_code: str | None = Field(default=None, min_length=2, max_length=64)
    email: str
    password: str = Field(min_length=1, max_length=256)

    @field_validator("company_code")
    @classmethod
    def normalize_company_code(cls, v: str | None) -> str | None:
        if v is None:
            return None
        value = v.strip().lower()
        return value or None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


class TokenResponse(BaseModel):
    """Token response for API clients (mobile apps, CLI tools) - NOT for browser auth."""
    access_token: str
    refresh_token: str
    csrf_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class LoginResponse(BaseModel):
    """Login response for browser-based cookie auth.

    Does NOT include access/refresh tokens - they are stored in HTTPOnly cookies.
    Includes CSRF token for state-changing operations.
    """
    user: MeResponse
    csrf_token: str | None = None
    expires_in: int  # Access token expiry time for UI countdown
    require_password_change: bool = False  # Force password change on first login
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"


class CompanyRegistrationResponse(BaseModel):
    """Response for successful company registration.
    
    Returns user_id for email verification instead of tokens.
    User must verify email before accessing the system.
    """
    user_id: str
    message: str = "Registration successful. Please check your email for verification code."
    requires_verification: bool = True
    company: dict[str, str] | None = None


class VerifyEmailRequest(BaseModel):
    """Request to verify email with OTP code."""
    user_id: str
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendVerificationRequest(BaseModel):
    """Request to resend verification code."""
    user_id: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10, max_length=2048)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10, max_length=2048)


class MeResponse(BaseModel):
    id: str
    tenant_id: str
    tenant_code: str
    tenant_name: str
    email: str
    full_name: str
    roles: list[str]
    is_active: bool
    is_platform_owner: bool
    require_password_change: bool = False


class CompanyRegistrationRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    company_code: str = Field(min_length=2, max_length=64)
    admin_email: str
    admin_password: str = Field(min_length=12, max_length=256)
    admin_full_name: str = Field(min_length=2, max_length=200)

    @field_validator("company_code")
    @classmethod
    def validate_company_code(cls, v: str) -> str:
        value = v.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$", value):
            raise ValueError("Company code must use lowercase letters, digits, and hyphen")
        return value

    @field_validator("admin_email")
    @classmethod
    def validate_admin_email(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


class InvitationAcceptRequest(BaseModel):
    invitation_token: str = Field(min_length=20, max_length=512)
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=12, max_length=256)
