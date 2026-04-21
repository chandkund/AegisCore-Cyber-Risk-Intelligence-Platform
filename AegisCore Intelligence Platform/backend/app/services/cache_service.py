"""Redis caching service for performance optimization.

Caches:
- Dashboard analytics data
- Risk trends
- SLA forecasts
- Top risks
- Severity distributions

Uses tenant-aware keys for multi-tenant isolation.
"""

from __future__ import annotations

import json
import os
from functools import wraps
from typing import Any, Callable, TypeVar
from uuid import UUID

import redis
from fastapi import Depends

# Redis configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL_SHORT = 60  # 1 minute for real-time data
CACHE_TTL_MEDIUM = 300  # 5 minutes for semi-static data
CACHE_TTL_LONG = 1800  # 30 minutes for static data

F = TypeVar("F", bound=Callable[..., Any])


class CacheService:
    """Redis-based caching service with tenant isolation."""

    _instance = None
    _redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    health_check_interval=30,
                )
                # Test connection
                self._redis_client.ping()
            except redis.ConnectionError:
                # Fallback to null cache if Redis unavailable
                self._redis_client = None

    def _get_key(self, tenant_id: UUID | str, prefix: str, identifier: str) -> str:
        """Generate cache key with tenant isolation."""
        return f"aegiscore:{tenant_id}:{prefix}:{identifier}"

    def get(self, tenant_id: UUID | str, prefix: str, identifier: str) -> Any | None:
        """Get cached value."""
        if not self._redis_client:
            return None

        try:
            key = self._get_key(tenant_id, prefix, identifier)
            data = self._redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except redis.RedisError:
            return None

    def set(
        self,
        tenant_id: UUID | str,
        prefix: str,
        identifier: str,
        value: Any,
        ttl: int = CACHE_TTL_MEDIUM,
    ) -> bool:
        """Set cached value."""
        if not self._redis_client:
            return False

        try:
            key = self._get_key(tenant_id, prefix, identifier)
            self._redis_client.setex(key, ttl, json.dumps(value))
            return True
        except redis.RedisError:
            return False

    def delete(self, tenant_id: UUID | str, prefix: str, identifier: str) -> bool:
        """Delete cached value."""
        if not self._redis_client:
            return False

        try:
            key = self._get_key(tenant_id, prefix, identifier)
            self._redis_client.delete(key)
            return True
        except redis.RedisError:
            return False

    def delete_pattern(self, tenant_id: UUID | str, pattern: str) -> int:
        """Delete all keys matching pattern for tenant."""
        if not self._redis_client:
            return 0

        try:
            search_pattern = f"aegiscore:{tenant_id}:{pattern}:*"
            keys = self._redis_client.keys(search_pattern)
            if keys:
                return self._redis_client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0

    def invalidate_tenant_cache(self, tenant_id: UUID | str) -> int:
        """Invalidate all cache for a tenant."""
        if not self._redis_client:
            return 0

        try:
            pattern = f"aegiscore:{tenant_id}:*"
            keys = self._redis_client.keys(pattern)
            if keys:
                return self._redis_client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0

    def flush_all(self) -> bool:
        """Flush all cache (use with caution)."""
        if not self._redis_client:
            return False

        try:
            self._redis_client.flushdb()
            return True
        except redis.RedisError:
            return False


def cached(
    prefix: str,
    ttl: int = CACHE_TTL_MEDIUM,
    key_func: Callable | None = None,
):
    """Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_func: Optional function to generate cache key from arguments
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = CacheService()

            # Extract tenant_id from arguments
            # Assumes first arg is tenant_id or kwargs contains tenant_id
            tenant_id = kwargs.get("tenant_id")
            if not tenant_id and args:
                tenant_id = args[0] if isinstance(args[0], (UUID, str)) else None

            if not tenant_id:
                # Can't cache without tenant isolation
                return func(*args, **kwargs)

            # Generate cache key
            if key_func:
                identifier = key_func(*args, **kwargs)
            else:
                # Default: use function name and args
                identifier = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"

            # Try to get from cache
            cached_value = cache.get(tenant_id, prefix, identifier)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(tenant_id, prefix, identifier, result, ttl)

            return result

        # Add cache invalidation method
        wrapper.invalidate_cache = lambda tenant_id: CacheService().delete_pattern(
            tenant_id, prefix
        )

        return wrapper
    return decorator


def invalidate_on_change(prefix: str):
    """Decorator to invalidate cache after successful modification."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Extract tenant_id and invalidate cache
            tenant_id = kwargs.get("tenant_id")
            if not tenant_id and args:
                tenant_id = args[0] if isinstance(args[0], (UUID, str)) else None

            if tenant_id:
                cache = CacheService()
                cache.delete_pattern(tenant_id, prefix)

            return result

        return wrapper
    return decorator


# Singleton instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get or create cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
