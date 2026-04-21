"""CSRF protection middleware for state-changing requests.

Implements double-submit cookie pattern with:
- CSRF token in cookie (HttpOnly=False, JavaScript readable)
- CSRF token in header (X-CSRF-Token)
- Token validation for state-changing methods
"""

from __future__ import annotations

import secrets
from typing import Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.middleware.base import BaseHTTPMiddleware

# State-changing HTTP methods that require CSRF protection
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware to protect against CSRF attacks.
    
    For state-changing requests (POST, PUT, PATCH, DELETE), validates
    that the X-CSRF-Token header matches the CSRF token in the cookie.
    
    For safe requests (GET, HEAD, OPTIONS), sets the CSRF cookie if not present.
    
    Attributes:
        secret_key: Secret key for signing CSRF tokens
        cookie_name: Name of the CSRF cookie
        header_name: Name of the CSRF header
        cookie_max_age: Max age of CSRF cookie in seconds
        token_max_age: Max age of token for validation in seconds
    """

    def __init__(
        self,
        app,
        secret_key: str,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        cookie_max_age: int = 3600,  # 1 hour
        token_max_age: int = 60,  # 1 minute for validation
        exempt_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.serializer = URLSafeTimedSerializer(secret_key)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.cookie_max_age = cookie_max_age
        self.token_max_age = token_max_age
        self.exempt_paths = exempt_paths or set()

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection."""
        # API documentation and health endpoints are exempt
        exempt_prefixes = {
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
            "/api/v1/auth/login",  # Login doesn't need CSRF (no session yet)
            "/api/v1/auth/register",
            "/api/v1/auth/register-company",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/resend-verification",
            "/api/v1/auth/accept-invitation",
            "/api/v1/auth/refresh",
            "/api/v1/auth/logout",
        }
        return any(path.startswith(prefix) for prefix in exempt_prefixes) or path in self.exempt_paths

    def _generate_token(self) -> str:
        """Generate a new CSRF token."""
        return secrets.token_urlsafe(32)

    def _set_csrf_cookie(self, response: Response, token: str, *, secure: bool) -> None:
        """Set the CSRF token cookie.
        
        Note: HttpOnly=False so JavaScript can read it to send in header.
        Secure=True requires HTTPS in production.
        SameSite=strict prevents cross-site cookie sending.
        """
        signed_token = self.serializer.dumps(token)
        response.set_cookie(
            key=self.cookie_name,
            value=signed_token,
            max_age=self.cookie_max_age,
            httponly=False,  # JavaScript needs to read this
            secure=secure,  # Only force secure cookies for HTTPS requests
            samesite="strict",
            path="/",
        )

    def _validate_csrf_token(self, request: Request) -> None:
        """Validate CSRF token from cookie and header.
        
        Raises:
            HTTPException: If token is missing, invalid, or mismatched.
        """
        # Get token from cookie
        cookie_token_signed = request.cookies.get(self.cookie_name)
        if not cookie_token_signed:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing from cookie",
            )

        # Get token from header
        header_token_signed = request.headers.get(self.header_name)
        if not header_token_signed:
            raise HTTPException(
                status_code=403,
                detail=f"CSRF token missing from header ({self.header_name})",
            )

        # Unsign and validate cookie token
        try:
            cookie_token = self.serializer.loads(
                cookie_token_signed, max_age=self.cookie_max_age
            )
        except SignatureExpired:
            raise HTTPException(
                status_code=403,
                detail="CSRF token cookie expired",
            )
        except BadSignature:
            raise HTTPException(
                status_code=403,
                detail="Invalid CSRF token cookie",
            )

        # Unsign and validate header token
        try:
            header_token = self.serializer.loads(
                header_token_signed, max_age=self.token_max_age
            )
        except SignatureExpired:
            raise HTTPException(
                status_code=403,
                detail="CSRF token header expired",
            )
        except BadSignature:
            raise HTTPException(
                status_code=403,
                detail="Invalid CSRF token header",
            )

        # Compare tokens
        if not secrets.compare_digest(cookie_token, header_token):
            raise HTTPException(
                status_code=403,
                detail="CSRF token mismatch",
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and apply CSRF protection."""
        path = request.url.path
        method = request.method
        is_https = request.url.scheme == "https"

        # Skip exempt paths
        if self._is_exempt(path):
            response = await call_next(request)
            # Still set CSRF cookie for safe methods on exempt paths
            if method in ("GET", "HEAD") and self.cookie_name not in request.cookies:
                token = self._generate_token()
                self._set_csrf_cookie(response, token, secure=is_https)
            return response

        # For safe methods (GET, HEAD, OPTIONS), just ensure CSRF cookie is set
        if method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)
            if self.cookie_name not in request.cookies:
                token = self._generate_token()
                self._set_csrf_cookie(response, token, secure=is_https)
            return response

        # For state-changing methods, validate CSRF token
        if method in STATE_CHANGING_METHODS:
            # Bearer-token authenticated APIs are not susceptible to browser CSRF in the same way
            # as cookie-auth flows; skip CSRF token checks when explicit Authorization is used.
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.lower().startswith("bearer "):
                try:
                    self._validate_csrf_token(request)
                except HTTPException as exc:
                    response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
                    # Preserve baseline security headers even when CSRF blocks request
                    response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
                    response.headers.setdefault("X-Frame-Options", "DENY")
                    return response

        # Process request
        response = await call_next(request)

        # Refresh CSRF cookie after successful state-changing request
        if method in STATE_CHANGING_METHODS and self.cookie_name in request.cookies:
            token = self._generate_token()
            self._set_csrf_cookie(response, token, secure=is_https)

        return response


class CSRFTokenGenerator:
    """Utility to generate CSRF tokens for frontend use.
    
    This can be used in endpoints that need to provide a CSRF token
    to the frontend (e.g., after login).
    """

    def __init__(self, secret_key: str):
        self.serializer = URLSafeTimedSerializer(secret_key)

    def generate_token(self) -> str:
        """Generate a new CSRF token."""
        token = secrets.token_urlsafe(32)
        return self.serializer.dumps(token)

    def validate_token(self, token: str, max_age: int = 60) -> bool:
        """Validate a CSRF token."""
        try:
            self.serializer.loads(token, max_age=max_age)
            return True
        except (BadSignature, SignatureExpired):
            return False
