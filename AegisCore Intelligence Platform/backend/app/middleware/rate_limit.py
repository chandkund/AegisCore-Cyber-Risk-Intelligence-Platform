"""Rate limiting using slowapi with Redis support.

Provides strict rate limits for authentication endpoints.
"""

from __future__ import annotations

import os
from typing import Optional

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request, HTTPException, status

# Initialize limiter with Redis if available, otherwise memory
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    from slowapi.util import get_redis
    storage_uri = f"redis+{redis_url}"
else:
    storage_uri = "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=["120 per minute"],
    strategy="moving-window",  # More accurate than fixed-window
)


def get_auth_limit_key(request: Request) -> str:
    """Get rate limit key for auth endpoints (IP + email if available)."""
    client_ip = get_remote_address(request)
    
    # Try to extract email/username from request body for login attempts
    # This prevents distributed brute force attacks
    try:
        body = request.scope.get("body", b"")
        if body:
            import json
            data = json.loads(body.decode())
            email = data.get("email", "").lower().strip()
            if email:
                return f"auth:{email}:{client_ip}"
    except Exception:
        pass
    
    return f"auth:{client_ip}"


# Rate limit configurations
LOGIN_LIMIT = "5 per minute"
REGISTER_LIMIT = "3 per minute"
VERIFY_LIMIT = "10 per minute"
PASSWORD_RESET_LIMIT = "3 per minute"
UPLOAD_LIMIT = "10 per minute"
SENSITIVE_LIMIT = "30 per minute"


def get_endpoint_limit(path: str, method: str) -> Optional[str]:
    """Get rate limit for specific endpoint."""
    if method != "POST":
        return None
    
    # Auth endpoints - strict limits
    if "/auth/login" in path:
        return LOGIN_LIMIT
    elif "/auth/register" in path:
        return REGISTER_LIMIT
    elif "/auth/verify" in path:
        return VERIFY_LIMIT
    elif "/auth/password-reset" in path or "/auth/forgot-password" in path:
        return PASSWORD_RESET_LIMIT
    elif "/upload" in path:
        return UPLOAD_LIMIT
    elif "/auth/" in path:
        return SENSITIVE_LIMIT
    
    return None


def reset_for_tests() -> None:
    """Reset rate limiter (for testing only)."""
    limiter.reset()
