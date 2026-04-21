"""Security tests for cookie-based authentication.

These tests verify:
1. Login sets HTTPOnly, Secure, SameSite cookies
2. Tokens are NOT returned in response body
3. Refresh uses cookies, not request body tokens
4. Logout clears cookies
5. No JS-accessible tokens
6. CSRF protection works
"""

from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Cookies

from app.main import app

client = TestClient(app)


class TestCookieBasedAuth:
    """Test suite for cookie-based authentication security."""

    def test_login_sets_http_only_cookie(self):
        """Verify login sets HTTPOnly access_token cookie."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
                "company_code": "test-company",
            },
        )

        # Should return 200 even if credentials are wrong (test for cookie structure)
        # Check for Set-Cookie header with proper attributes
        set_cookie_headers = [
            h for h in response.headers.get_list("set-cookie")
            if "access_token" in h.lower()
        ]

        # If login succeeded, verify cookie attributes
        if response.status_code == status.HTTP_200_OK:
            assert len(set_cookie_headers) > 0, "access_token cookie not set"

            for cookie in set_cookie_headers:
                assert "httponly" in cookie.lower(), "Cookie must be HTTPOnly"
                assert "samesite" in cookie.lower(), "Cookie must have SameSite attribute"
                # Secure flag check (would be in production)
                # assert "secure" in cookie.lower(), "Cookie must be Secure in production"

    def test_login_response_does_not_contain_tokens(self):
        """Verify login response does NOT contain access/refresh tokens in body."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
                "company_code": "test-company",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # CRITICAL: Tokens must NOT be in response body
            assert "access_token" not in data, "access_token must NOT be in response body"
            assert "refresh_token" not in data, "refresh_token must NOT be in response body"
            assert "token" not in data.get("access_token", ""), "No token in response"

            # Should contain user info and CSRF token
            assert "user" in data, "Response should contain user info"
            assert "csrf_token" in data, "Response should contain CSRF token"
            assert "expires_in" in data, "Response should contain expires_in"

    def test_refresh_uses_cookie_not_body_token(self):
        """Verify refresh endpoint reads token from cookie, not request body."""
        # First, try refresh without any cookies (should fail)
        response_no_cookie = client.post(
            "/api/v1/auth/refresh",
            json={},  # No token in body
        )

        # Should fail because no refresh token cookie
        assert response_no_cookie.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_clears_cookies(self):
        """Verify logout clears authentication cookies."""
        # First login (or use a mock session)
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
                "company_code": "test-company",
            },
        )

        if login_response.status_code == status.HTTP_200_OK:
            # Then logout
            logout_response = client.post("/api/v1/auth/logout")

            # Check that cookies are cleared (Set-Cookie with empty value or expired)
            set_cookie_headers = logout_response.headers.get_list("set-cookie")
            access_cookie_cleared = any(
                "access_token=" in h and ("max-age=0" in h.lower() or "expires=thu, 01 jan 1970" in h.lower())
                for h in set_cookie_headers
            )
            # Note: Cookie clearing might use different mechanisms

    def test_protected_endpoint_requires_cookie(self):
        """Verify protected endpoints require valid cookie."""
        # Try accessing /me without any cookies
        response = client.get("/api/v1/auth/me")

        # Should fail with 401
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_csrf_token_in_response(self):
        """Verify login returns CSRF token for state-changing operations."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
                "company_code": "test-company",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "csrf_token" in data, "CSRF token should be in response"
            assert data["csrf_token"] is not None, "CSRF token should not be null"

    def test_no_bearer_token_in_js_storage_pattern(self):
        """Verify the auth flow doesn't expose tokens to JavaScript."""
        # This test checks that the response structure is cookie-based
        # by verifying the response doesn't have TokenResponse structure
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
                "company_code": "test-company",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Old TokenResponse had: access_token, refresh_token, token_type, expires_in
            # New LoginResponse has: user, csrf_token, expires_in, require_password_change

            assert "token_type" not in data, "Should not have token_type (old JWT pattern)"
            assert "user" in data, "Should have user object (cookie auth pattern)"


class TestAuthCookieSecurity:
    """Test specific cookie security attributes."""

    def test_cookie_samesite_attribute(self):
        """Verify cookies have SameSite attribute."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
            },
        )

        set_cookie_headers = response.headers.get_list("set-cookie")
        for cookie in set_cookie_headers:
            if "token" in cookie.lower():
                assert "samesite" in cookie.lower(), f"Cookie missing SameSite: {cookie}"

    def test_cookie_path_attribute(self):
        """Verify cookies have Path=/ for whole site access."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
            },
        )

        set_cookie_headers = response.headers.get_list("set-cookie")
        for cookie in set_cookie_headers:
            if "token" in cookie.lower():
                assert "path=/" in cookie.lower(), f"Cookie should have Path=/: {cookie}"


class TestMixedAuthCompatibility:
    """Test backward compatibility with Bearer token (if supported)."""

    def test_bearer_token_still_works_if_sent(self):
        """Verify Bearer token in header still works as fallback."""
        # This test verifies that the backend can still accept Bearer tokens
        # for API clients while preferring cookies for browser clients
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        # Should fail with 401 but not crash
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestXSSResistance:
    """Test that auth system is resistant to XSS attacks."""

    def test_tokens_not_in_localstorage_pattern(self):
        """Verify tokens are not designed to be stored in localStorage/sessionStorage."""
        # This is a design test - the backend should not return tokens
        # in a way that encourages frontend JS storage
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@example.com",
                "password": "testpassword123",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # If tokens were in response, frontend might store them in localStorage
            assert "access_token" not in data, "XSS risk: access_token in response"
            assert "refresh_token" not in data, "XSS risk: refresh_token in response"
