from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.api.deps import Principal, get_current_user
from app.core import rbac
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.deps import get_db
from app.middleware.login_rate_limit import allow_login_attempt
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    CompanyRegistrationRequest,
    CompanyRegistrationResponse,
    InvitationAcceptRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    ResendVerificationRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.otp_service import (
    OTPError,
    OTPExpiredError,
    OTPInvalidError,
    OTPMaxAttemptsError,
    OTPAlreadyVerifiedError,
    OTPRateLimitError,
    OTPService,
)
from app.services.password_validation_service import validate_password_strength
from app.middleware.csrf_protection import CSRFTokenGenerator
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/auth", tags=["auth"])


def _role_names(user: object) -> list[str]:
    return sorted(
        ur.role.name
        for ur in getattr(user, "roles", [])
        if getattr(ur, "role", None) is not None and getattr(ur.role, "name", None)
    )

def _issue_csrf_token() -> str:
    settings = get_settings()
    return CSRFTokenGenerator(settings.jwt_secret_key).generate_token()

def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    settings = get_settings()
    secure = settings.app_env == "production" or settings.app_env == "staging"
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        max_age=3600,
        httponly=False,
        secure=secure,
        samesite="strict",
        path="/",
    )


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str, expires_in: int) -> None:
    """Set secure HTTP-only cookies for authentication tokens.
    
    These cookies provide defense in depth alongside the JSON response tokens.
    They are:
    - HttpOnly: Not accessible to JavaScript (XSS protection)
    - Secure: Only sent over HTTPS in production
    - SameSite=strict: Only sent to same origin (CSRF protection)
    - Path=/: Available to all routes
    """
    settings = get_settings()
    
    # Determine if we should use secure cookies (always in production)
    secure = settings.app_env == "production" or settings.app_env == "staging"
    
    # Set access token cookie (short-lived)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=expires_in,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )
    
    # Set refresh token cookie (longer-lived)
    # Refresh tokens typically valid for 7 days
    refresh_max_age = 7 * 24 * 60 * 60  # 7 days in seconds
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_max_age,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/api/v1/auth/refresh",  # Only sent to refresh endpoint
    )


def _legacy_tokens_for_response(access: str, refresh: str) -> tuple[str | None, str | None]:
    settings = get_settings()
    if settings.app_env in {"production", "staging"}:
        return None, None
    return access, refresh


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> Response:
    """Authenticate user and set HTTPOnly cookies.

    Access/refresh tokens are stored in secure HTTPOnly cookies (not accessible to JS).
    Response includes user info and CSRF token for state-changing operations.
    """
    client = request.client.host if request.client else "unknown"
    if not allow_login_attempt(client):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts; try again shortly",
        )
    try:
        access, refresh, expires_in = AuthService(db).login(
            body.email, body.password, company_code=body.company_code
        )
    except ValueError:
        AuditService(db).record(
            actor_user_id=None,
            actor_email=body.email.strip().lower(),
            action="login_failed",
            resource_type="authentication",
            payload={"company_code": body.company_code},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Build user principal from token (before cookies are set)
    from app.core.security import decode_access_token
    payload = decode_access_token(access)
    user_id = payload["sub"]
    tenant_id = payload.get("tid")
    roles = payload.get("roles", [])

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(uuid.UUID(user_id))

    AuditService(db).record(
        actor_user_id=user.id if user else None,
        actor_email=body.email.strip().lower(),
        actor_role=sorted(roles)[0] if roles else None,
        action="login_success",
        resource_type="authentication",
        tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
        payload={"company_code": body.company_code},
    )
    db.commit()

    # Issue CSRF token for state-changing operations
    csrf_token = _issue_csrf_token()

    # Build user response
    from app.repositories.organization_repository import OrganizationRepository
    org_repo = OrganizationRepository(db)
    org = org_repo.get_by_id(uuid.UUID(tenant_id)) if tenant_id else None

    user_roles = _role_names(user) if user else []
    user_response = MeResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else "",
        tenant_code=org.code if org else "",
        tenant_name=org.name if org else "",
        email=user.email,
        full_name=user.full_name,
        roles=user_roles,
        is_active=user.is_active,
        is_platform_owner=rbac.ROLE_PLATFORM_OWNER in user_roles,
        require_password_change=user.require_password_change,
    ) if user else None

    # Create response WITHOUT tokens in body (tokens only in cookies)
    legacy_access, legacy_refresh = _legacy_tokens_for_response(access, refresh)
    response = Response(
        content=LoginResponse(
            user=user_response,
            csrf_token=csrf_token,
            expires_in=expires_in,
            require_password_change=user.require_password_change if user else False,
            access_token=legacy_access,
            refresh_token=legacy_refresh,
        ).model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )

    # Set secure HTTP-only cookies (tokens NOT in response body)
    _set_auth_cookies(response, access, refresh, expires_in)
    _set_csrf_cookie(response, csrf_token)

    return response


@router.post("/refresh", response_model=LoginResponse)
def refresh_token(
    request: Request,
    body: RefreshRequest = Body(default_factory=RefreshRequest),
    db: Session = Depends(get_db),
) -> Response:
    """Refresh access token using cookie or request body refresh token.

    Returns user info with CSRF token - access/refresh tokens only in cookies.
    """
    refresh_token_value = body.refresh_token or request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    try:
        access, refresh, expires_in = AuthService(db).refresh(refresh_token_value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Decode new token to get user info
    from app.core.security import decode_access_token
    from app.repositories.user_repository import UserRepository
    from app.repositories.organization_repository import OrganizationRepository

    payload = decode_access_token(access)
    user_id = payload["sub"]
    tenant_id = payload.get("tid")

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(uuid.UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Build user response
    org_repo = OrganizationRepository(db)
    org = org_repo.get_by_id(uuid.UUID(tenant_id)) if tenant_id else None

    user_roles = _role_names(user)
    user_response = MeResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id) if user.tenant_id else "",
        tenant_code=org.code if org else "",
        tenant_name=org.name if org else "",
        email=user.email,
        full_name=user.full_name,
        roles=user_roles,
        is_active=user.is_active,
        is_platform_owner=rbac.ROLE_PLATFORM_OWNER in user_roles,
        require_password_change=user.require_password_change,
    )

    # Issue new CSRF token
    csrf_token = _issue_csrf_token()

    # Create response WITHOUT tokens in body
    legacy_access, legacy_refresh = _legacy_tokens_for_response(access, refresh)
    response = Response(
        content=LoginResponse(
            user=user_response,
            csrf_token=csrf_token,
            expires_in=expires_in,
            require_password_change=user.require_password_change,
            access_token=legacy_access,
            refresh_token=legacy_refresh,
        ).model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )

    # Set secure HTTP-only cookies with new tokens
    _set_auth_cookies(response, access, refresh, expires_in)
    _set_csrf_cookie(response, csrf_token)

    return response


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies on logout."""
    settings = get_settings()
    secure = settings.app_env == "production" or settings.app_env == "staging"

    # Clear access token cookie
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=secure,
        samesite="strict",
    )
    
    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth/refresh",
        httponly=True,
        secure=secure,
        samesite="strict",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(
    request: Request,
    body: LogoutRequest = Body(default_factory=LogoutRequest),
    db: Session = Depends(get_db),
) -> Response:
    refresh_token_value = body.refresh_token or request.cookies.get("refresh_token")
    try:
        if refresh_token_value:
            AuthService(db).logout(refresh_token_value)
    except Exception:  # noqa: BLE001 — idempotent logout
        pass
    
    # Create response and clear cookies
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response)
    
    return response


@router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.oltp import User
    
    user = db.get(User, principal.id)
    require_password_change = user.require_password_change if user else False
    
    return MeResponse(
        id=str(principal.id),
        tenant_id=str(principal.tenant_id),
        tenant_code=principal.tenant_code,
        tenant_name=principal.tenant_name,
        email=principal.email,
        full_name=principal.full_name,
        roles=sorted(principal.roles),
        is_active=True,
        is_platform_owner="platform_owner" in principal.roles,
        require_password_change=require_password_change,
    )


@router.post("/register-company", response_model=CompanyRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_company(body: CompanyRegistrationRequest, db: Session = Depends(get_db)) -> CompanyRegistrationResponse:
    """Register a new company with admin user.
    
    Returns user_id for email verification. User must verify email with OTP before accessing the system.
    """
    service = AuthService(db)
    try:
        user_id, otp_code = service.register_company(
            company_name=body.company_name,
            company_code=body.company_code,
            admin_email=body.admin_email,
            admin_password=body.admin_password,
            admin_full_name=body.admin_full_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
    # Log OTP for development (in production, this would be emailed)
    print(f"[DEV] Verification code for {body.admin_email}: {otp_code}")
    
    response = CompanyRegistrationResponse(
        user_id=str(user_id),
        message="Registration successful. Please check your email for verification code.",
        requires_verification=True,
        company={"code": body.company_code, "name": body.company_name},
    )
    return response


@router.post("/verify-email", response_model=TokenResponse)
def verify_email(body: VerifyEmailRequest, db: Session = Depends(get_db)) -> Response:
    """Verify email with 6-digit OTP code and auto-login."""
    try:
        access, refresh, expires_in = AuthService(db).verify_email(
            user_id=uuid.UUID(body.user_id),
            code=body.code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
    # Create response with tokens
    csrf_token = _issue_csrf_token()
    response = Response(
        content=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            csrf_token=csrf_token,
            expires_in=expires_in,
        ).model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
    
    # Set secure HTTP-only cookies
    _set_auth_cookies(response, access, refresh, expires_in)
    _set_csrf_cookie(response, csrf_token)
    
    return response


@router.post("/resend-verification", response_model=dict)
def resend_verification(body: ResendVerificationRequest, db: Session = Depends(get_db)) -> dict:
    """Resend verification code to user email."""
    try:
        new_code = AuthService(db).resend_verification_code(user_id=uuid.UUID(body.user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
    print(f"[DEV] New verification code: {new_code}")
    
    return {
        "message": "A new verification code has been sent to your email.",
        "expires_in_minutes": 15,
    }


@router.post("/accept-invitation", response_model=TokenResponse)
def accept_invitation(body: InvitationAcceptRequest, db: Session = Depends(get_db)) -> Response:
    try:
        access, refresh, expires_in = AuthService(db).accept_invitation(
            invitation_token=body.invitation_token,
            full_name=body.full_name,
            password=body.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
    # Create response with tokens in body
    csrf_token = _issue_csrf_token()
    response = Response(
        content=TokenResponse(
            access_token=access,
            refresh_token=refresh,
            csrf_token=csrf_token,
            expires_in=expires_in,
        ).model_dump_json(),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
    
    # Set secure HTTP-only cookies
    _set_auth_cookies(response, access, refresh, expires_in)
    _set_csrf_cookie(response, csrf_token)
    
    return response


# ============================================================================
# Password Validation and Strength Endpoints
# ============================================================================

class PasswordValidationRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=128)
    email: str | None = None
    name: str | None = None


class PasswordValidationResponse(BaseModel):
    is_valid: bool
    strength: str
    score: int
    errors: list[str]
    suggestions: list[str]
    label: str
    color: str
    min_length: int
    max_length: int


@router.post("/validate-password", response_model=PasswordValidationResponse)
def validate_password(body: PasswordValidationRequest):
    """Validate password strength in real-time.
    
    This endpoint can be called as the user types to provide
    immediate feedback on password strength.
    """
    result = validate_password_strength(
        password=body.password,
        user_email=body.email,
        user_name=body.name,
    )
    return PasswordValidationResponse(**result)


# ============================================================================
# Email Verification OTP Endpoints
# ============================================================================

class OTPVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class OTPVerifyResponse(BaseModel):
    success: bool
    message: str
    verified: bool


class OTPStatusResponse(BaseModel):
    verified: bool
    email: str | None
    pending_otp: bool
    otp_expires_at: str | None
    otp_attempts: int
    otp_max_attempts: int
    can_resend: bool
    resend_seconds_remaining: int


class OTPResendResponse(BaseModel):
    success: bool
    message: str
    can_resend_at: str | None = None


class LegacyRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=12, max_length=256)
    full_name: str = Field(..., min_length=2, max_length=200)
    organization_code: str = Field(..., min_length=2, max_length=64)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_legacy(body: dict = Body(...), db: Session = Depends(get_db)):
    """Legacy registration endpoint kept for backwards compatibility.

    Supports:
    - Legacy user registration payload (`email`, `password`, `full_name`, `organization_code`)
    - Legacy company registration payload (`company_name`, `company_code`, `admin_email`, ...)
    """
    if "company_name" in body and "company_code" in body and "admin_email" in body:
        company_body = CompanyRegistrationRequest(
            company_name=body["company_name"],
            company_code=body["company_code"],
            admin_email=body["admin_email"],
            admin_password=body.get("admin_password", body.get("password", "")),
            admin_full_name=body.get("admin_full_name", body.get("admin_name", "")),
        )
        return register_company(company_body, db)

    try:
        typed_body = LegacyRegisterRequest(**body)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    from sqlalchemy import select
    from app.models.oltp import Organization, Role, User, UserRole

    org = db.execute(
        select(Organization).where(Organization.code == typed_body.organization_code.strip().lower())
    ).scalar_one_or_none()
    if org is None or not org.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    email = typed_body.email.strip().lower()
    existing = db.execute(
        select(User).where(User.tenant_id == org.id, User.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    pwd = validate_password_strength(password=typed_body.password, user_email=email, user_name=typed_body.full_name)
    if not pwd["is_valid"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=pwd["errors"])

    user = User(
        email=email,
        tenant_id=org.id,
        full_name=typed_body.full_name.strip(),
        hashed_password=hash_password(typed_body.password),
        is_active=True,
        email_verified=False,
    )
    db.add(user)
    db.flush()

    analyst_role = db.execute(select(Role).where(Role.name == rbac.ROLE_ANALYST)).scalar_one_or_none()
    if analyst_role is not None:
        db.add(UserRole(user_id=user.id, role_id=analyst_role.id))
    db.commit()

    return {"id": str(user.id), "email": user.email, "full_name": user.full_name}


@router.get("/verification-status", response_model=OTPStatusResponse)
def get_verification_status(
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current email verification status for authenticated user."""
    service = OTPService(db)
    status = service.get_verification_status(principal.id)
    return OTPStatusResponse(**status)


@router.post("/otp/verify-email", response_model=OTPVerifyResponse)
def verify_email(
    body: OTPVerifyRequest,
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify email with 6-digit OTP code.
    
    - Code must be 6 digits
    - Max 5 attempts per OTP
    - OTP expires after 10 minutes
    """
    service = OTPService(db)
    try:
        service.verify(user_id=principal.id, raw_code=body.code)
        return OTPVerifyResponse(
            success=True,
            message="Email verified successfully",
            verified=True,
        )
    except OTPAlreadyVerifiedError as e:
        return OTPVerifyResponse(
            success=True,
            message=str(e),
            verified=True,
        )
    except OTPExpiredError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except OTPMaxAttemptsError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except (OTPInvalidError, OTPError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/otp/resend-verification", response_model=OTPResendResponse)
def resend_verification(
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resend email verification OTP.
    
    Rate limited: Can only request new OTP every 60 seconds.
    """
    service = OTPService(db)
    try:
        # Generate new OTP (returns raw code - would be sent via email in production)
        raw_code = service.resend(user_id=principal.id, user_email=principal.email)
        
        # In production, send email here. For now, return code in development.
        # NEVER return raw code in production!
        return OTPResendResponse(
            success=True,
            message="Verification code sent to your email",
            can_resend_at=None,
        )
    except OTPAlreadyVerifiedError as e:
        return OTPResendResponse(
            success=True,
            message=str(e),
        )
    except OTPRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except OTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/request-verification", response_model=OTPResendResponse)
def request_verification(
    principal: Principal = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request initial email verification OTP."""
    service = OTPService(db)
    
    # Check if already verified
    status = service.get_verification_status(principal.id)
    if status["verified"]:
        return OTPResendResponse(
            success=True,
            message="Email is already verified",
        )
    
    try:
        raw_code = service.generate_and_store(principal.id)
        
        # In production, send email here
        return OTPResendResponse(
            success=True,
            message="Verification code sent to your email",
        )
    except OTPRateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except OTPError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
