"""Global API rate limiting per user/IP.

Uses in-memory sliding window. For production, consider Redis-based rate limiting.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import HTTPException, Request, status

_lock = threading.Lock()
# (identifier) -> [(timestamp, count)]
_buckets: Dict[str, List[Tuple[float, int]]] = defaultdict(list)

# Rate limits: (window_seconds, max_requests)
DEFAULT_LIMIT = (60, 120)  # 120 requests per minute
STRICT_LIMIT = (60, 30)    # 30 requests per minute for sensitive endpoints


def get_identifier(request: Request) -> str:
    """Get rate limit identifier from request."""
    # Try to get user ID from auth header
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        # Use token prefix as identifier (don't decode, just hash prefix)
        token = auth[7:15]  # First 8 chars of token
        return f"user:{token}"
    
    # Fall back to IP address
    client = request.client
    ip = client.host if client else "unknown"
    return f"ip:{ip}"


def check_rate_limit(
    identifier: str,
    window_seconds: int = 60,
    max_requests: int = 120,
) -> bool:
    """Check if request is within rate limit. Returns True if allowed."""
    now = time.monotonic()
    
    with _lock:
        bucket = _buckets[identifier]
        # Remove old entries outside window
        bucket[:] = [(t, c) for t, c in bucket if now - t < window_seconds]
        
        # Count total requests in window
        total = sum(c for _, c in bucket)
        
        if total >= max_requests:
            return False
        
        # Add current request
        bucket.append((now, 1))
        return True


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting."""
    # Skip health checks and docs
    path = request.url.path
    if path in ["/health", "/ready", "/api/v1/docs", "/api/v1/openapi.json"]:
        return await call_next(request)

    # Stricter limits for auth endpoints
    if "/auth/" in path and request.method == "POST":
        window, max_req = STRICT_LIMIT
    else:
        window, max_req = DEFAULT_LIMIT

    identifier = get_identifier(request)

    if not check_rate_limit(identifier, window, max_req):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(window)},
        )

    return await call_next(request)


def reset_for_tests() -> None:
    """Clear all rate limit buckets (for testing only)."""
    with _lock:
        _buckets.clear()
