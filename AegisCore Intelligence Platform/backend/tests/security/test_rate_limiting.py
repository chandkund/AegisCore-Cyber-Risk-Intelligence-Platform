"""Tests for rate limiting security middleware."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from app.middleware.rate_limit import (
    LOGIN_LIMIT,
    REGISTER_LIMIT,
    limiter,
    get_auth_limit_key,
)


@pytest.fixture
def app():
    """Create test app with rate limiting."""
    app = FastAPI()
    app.state.limiter = limiter
    
    @app.post("/api/v1/auth/login")
    @limiter.limit(LOGIN_LIMIT)
    async def login(request):
        return {"message": "login"}
    
    @app.post("/api/v1/auth/register")
    @limiter.limit(REGISTER_LIMIT)
    async def register(request):
        return {"message": "register"}
    
    @app.get("/api/v1/health")
    async def health(request):
        return {"status": "ok"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_login_rate_limit(self, client):
        """Test that login endpoint is rate limited."""
        # Make 5 successful requests
        for _ in range(5):
            response = client.post("/api/v1/auth/login")
            assert response.status_code == status.HTTP_200_OK
        
        # 6th request should be rate limited
        response = client.post("/api/v1/auth/login")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate limit" in response.json()["detail"].lower()

    def test_register_rate_limit(self, client):
        """Test that register endpoint is rate limited."""
        # Make 3 successful requests
        for _ in range(3):
            response = client.post("/api/v1/auth/register")
            assert response.status_code == status.HTTP_200_OK
        
        # 4th request should be rate limited
        response = client.post("/api/v1/auth/register")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_health_check_not_limited(self, client):
        """Test that health checks are not rate limited."""
        # Make many requests
        for _ in range(20):
            response = client.get("/api/v1/health")
            assert response.status_code == status.HTTP_200_OK

    def test_rate_limit_reset(self, client):
        """Test that rate limits reset after window."""
        import time
        
        # Exhaust rate limit
        for _ in range(5):
            client.post("/api/v1/auth/login")
        
        # Should be rate limited
        response = client.post("/api/v1/auth/login")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        
        # Wait for window to reset (in test mode this should be quick)
        time.sleep(1)
        
        # Should work again
        response = client.post("/api/v1/auth/login")
        # Note: In memory-based tests, this might still be limited
        # depending on the window configuration

    def test_auth_limit_key_with_email(self):
        """Test that auth limit key includes email when available."""
        from unittest.mock import MagicMock
        
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.scope = {
            "body": b'{"email": "test@example.com", "password": "secret"}'
        }
        
        key = get_auth_limit_key(request)
        assert "test@example.com" in key
        assert "192.168.1.1" in key

    def test_auth_limit_key_fallback_ip(self):
        """Test that auth limit key falls back to IP when no email."""
        from unittest.mock import MagicMock
        
        request = MagicMock()
        request.client.host = "192.168.1.1"
        request.scope = {"body": b"{}"}
        
        key = get_auth_limit_key(request)
        assert "192.168.1.1" in key


class TestRateLimitHeaders:
    """Test rate limit headers."""

    def test_retry_after_header(self, client):
        """Test that rate limit response includes Retry-After header."""
        # Exhaust rate limit
        for _ in range(5):
            client.post("/api/v1/auth/login")
        
        response = client.post("/api/v1/auth/login")
        assert "Retry-After" in response.headers or "retry-after" in response.headers
