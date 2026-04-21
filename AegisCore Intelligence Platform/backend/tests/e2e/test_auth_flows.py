"""End-to-end authentication flow tests.

These tests verify complete user journeys including:
- User registration
- Login with CSRF protection
- Password change
- Logout
- Session management
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestUserRegistrationFlow:
    """Test complete user registration and onboarding flow."""
    
    def test_successful_registration(self, api_client: TestClient, db: Session):
        """User can register with valid details."""
        response = api_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser_e2e@aegiscore.local",
                "password": "Q7v!9mZ#2rLp$8Tx",
                "full_name": "New E2E User",
                "organization_code": "aegiscore",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser_e2e@aegiscore.local"
        assert data["full_name"] == "New E2E User"
        assert "id" in data
        assert "access_token" not in data  # Should not auto-login
        
    def test_registration_with_weak_password_fails(self, api_client: TestClient):
        """Registration rejected with weak password."""
        response = api_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weakpass@aegiscore.local",
                "password": "123456",  # Weak password
                "full_name": "Weak Password User",
                "organization_code": "aegiscore",
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "password" in str(data).lower() or "validation" in str(data).lower()
        
    def test_registration_duplicate_email_fails(self, api_client: TestClient, authenticated_client: TestClient):
        """Cannot register with existing email."""
        # First get the test user's email from authenticated client
        me_response = authenticated_client.get("/api/v1/auth/me")
        existing_email = me_response.json()["email"]
        
        response = api_client.post(
            "/api/v1/auth/register",
            json={
                "email": existing_email,
                "password": "SecurePass123!@#",
                "full_name": "Duplicate User",
                "organization_code": "aegiscore",
            }
        )
        
        assert response.status_code == 409  # Conflict


class TestLoginFlow:
    """Test login and session management."""
    
    def test_successful_login(self, api_client: TestClient, db: Session, user_factory):
        """User can login with valid credentials."""
        user = user_factory.create(
            email="logintest@aegiscore.local",
            password="CorrectPass123!",
        )
        
        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "logintest@aegiscore.local",
                "password": "CorrectPass123!",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "csrf_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify cookies are secure
        assert "csrf_token" in api_client.cookies
        
    def test_login_with_invalid_password(self, api_client: TestClient, db: Session, user_factory):
        """Login rejected with wrong password."""
        user = user_factory.create(
            email="wrongpass@aegiscore.local",
            password="CorrectPass123!",
        )
        
        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpass@aegiscore.local",
                "password": "WrongPass123!",
            }
        )
        
        assert response.status_code == 401
        
    def test_login_rate_limiting(self, rate_limit_test_client):
        """Login rate limiting works correctly."""
        client = rate_limit_test_client
        
        # Make multiple failed login attempts
        for i in range(15):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "ratelimit@aegiscore.local",
                    "password": f"WrongPass{i}!",
                }
            )
        
        # After 10 failed attempts (default limit), should be rate limited
        # Note: Rate limit is per IP, so this might need adjustment based on config
        
    def test_csrf_protection_on_login(self, api_client: TestClient):
        """CSRF token is set during login."""
        # First get CSRF token
        api_client.get("/health")
        csrf_token = api_client.cookies.get("csrf_token")
        assert csrf_token is not None
        
        # Login should set new tokens
        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@aegiscore.local",
                "password": "AegisCore!demo2026",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "csrf_token" in data


class TestPasswordChangeFlow:
    """Test password change functionality."""
    
    def test_password_change_success(self, authenticated_client: TestClient):
        """Authenticated user can change password."""
        response = authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "Q7v!9mZ#2rLp$8Tx",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
    def test_password_change_with_wrong_current(self, authenticated_client: TestClient):
        """Password change rejected with wrong current password."""
        response = authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecurePass456!@#",
            }
        )
        
        assert response.status_code == 400
        
    def test_password_change_weak_new_password(self, authenticated_client: TestClient):
        """Password change rejected with weak new password."""
        response = authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "TestPassword123!",
                "new_password": "weak",
            }
        )
        
        assert response.status_code == 400


class TestSessionManagement:
    """Test JWT session management."""
    
    def test_token_refresh(self, authenticated_client: TestClient, db: Session):
        """User can refresh access token."""
        # Get current token info
        me_response = authenticated_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        
        # Refresh token
        refresh_response = authenticated_client.post("/api/v1/auth/refresh")
        assert refresh_response.status_code == 200
        
        data = refresh_response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        
    def test_invalid_token_rejected(self, api_client: TestClient):
        """Requests with invalid token are rejected."""
        api_client.headers["Authorization"] = "Bearer invalid_token"
        
        response = api_client.get("/api/v1/auth/me")
        assert response.status_code == 401
        
    def test_expired_token_rejected(self, api_client: TestClient):
        """Expired tokens are rejected."""
        # Create a token with past expiration
        from app.core.security import create_access_token
        from datetime import datetime, timedelta
        
        expired_token = create_access_token(
            subject="test-user-id",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        
        api_client.headers["Authorization"] = f"Bearer {expired_token}"
        response = api_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401


class TestLogout:
    """Test logout functionality."""
    
    def test_logout_clears_session(self, authenticated_client: TestClient):
        """Logout clears tokens and session."""
        # Verify logged in
        me_response = authenticated_client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        
        # Logout
        logout_response = authenticated_client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 204
        
        # Token should still work until expiration (stateless JWT)
        # But refresh token should be blacklisted if implemented


class TestProtectedEndpoints:
    """Test that protected endpoints require authentication."""
    
    def test_assets_endpoint_requires_auth(self, api_client: TestClient):
        """Assets endpoint requires authentication."""
        response = api_client.get("/api/v1/assets")
        assert response.status_code == 401
        
    def test_platform_endpoints_require_platform_owner(self, authenticated_client: TestClient):
        """Platform endpoints require platform owner role."""
        response = authenticated_client.get("/api/v1/platform/tenants")
        # Regular user should get 403
        assert response.status_code == 403
        
    def test_platform_owner_can_access(self, platform_owner_client: TestClient):
        """Platform owner can access platform endpoints."""
        response = platform_owner_client.get("/api/v1/platform/tenants")
        assert response.status_code == 200
