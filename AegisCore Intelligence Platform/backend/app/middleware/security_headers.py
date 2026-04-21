"""Security headers middleware for HTTP response hardening.

Adds essential security headers to all responses:
- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
"""

from __future__ import annotations

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all HTTP responses.
    
    These headers help protect against common web attacks:
    - Clickjacking (X-Frame-Options)
    - MIME sniffing (X-Content-Type-Options)
    - XSS (X-XSS-Protection, CSP)
    - Protocol downgrade (HSTS)
    - Information leakage (Referrer-Policy)
    
    Attributes:
        hsts_max_age: Max age for HSTS in seconds (default 1 year)
        hsts_include_subdomains: Whether to include subdomains in HSTS
        csp_directives: Content Security Policy directives
    """

    def __init__(
        self,
        app,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        enable_csp: bool = True,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.enable_csp = enable_csp

        # Build HSTS header value
        hsts_value = f"max-age={hsts_max_age}"
        if hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if hsts_preload:
            hsts_value += "; preload"
        self.hsts_value = hsts_value

        # CSP directive for API - stricter than frontend
        # For API responses, we mainly need to prevent content injection
        self.csp_value = (
            "default-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'none'; "
            "form-action 'none'"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # Forces HTTPS for all future requests
        response.headers["Strict-Transport-Security"] = self.hsts_value

        # Content-Security-Policy
        # Prevents XSS and data injection attacks
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = self.csp_value

        # X-Content-Type-Options
        # Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevents clickjacking by disallowing framing
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy but still useful)
        # Enables browser XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # Limits information leakage via Referer header
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy
        # Restricts browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Cache-Control for API responses
        # Prevent caching of sensitive data
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response
