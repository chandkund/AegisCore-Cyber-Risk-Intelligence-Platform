"""Full-stack API checks against a real PostgreSQL (migrated + seeded).

Set `AEGISCORE_TEST_DATABASE_URL` (e.g. same as local `DATABASE_URL`) to enable.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def _skip_if_no_db() -> str:
    url = os.getenv("AEGISCORE_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("AEGISCORE_TEST_DATABASE_URL not set")
    try:
        eng = create_engine(url.replace("postgresql+asyncpg", "postgresql+psycopg", 1))
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        eng.dispose()
    except Exception:
        pytest.skip("AEGISCORE_TEST_DATABASE_URL unreachable")
    return url


@pytest.fixture
def api_client(monkeypatch):
    url = _skip_if_no_db()
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv(
        "JWT_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "pytest-jwt-secret-key-32chars-min!!")
    )
    from importlib import reload

    import app.core.config as cfg
    import app.db.session as sess
    import app.main as main

    cfg.reset_settings_cache()
    sess.reset_engine()
    reload(cfg)
    reload(sess)
    reload(main)
    return TestClient(main.app)


def test_login_and_me(api_client: TestClient):
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]
    me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert me.status_code == 200
    assert "analyst" in me.json()["roles"]


def test_manager_forbidden_admin_route(api_client: TestClient):
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "manager@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    access = r.json()["access_token"]
    users = api_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert users.status_code == 403


def test_findings_list_requires_auth(api_client: TestClient):
    r = api_client.get("/api/v1/findings")
    assert r.status_code == 401


def test_refresh_token_rotation(api_client: TestClient):
    """Refresh token should rotate on use (new refresh token issued)."""
    # Login
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    data = r.json()
    original_refresh = data["refresh_token"]

    # Refresh the access token
    r = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert r.status_code == 200
    new_data = r.json()
    new_access = new_data["access_token"]
    new_refresh = new_data["refresh_token"]

    # New access token should work
    me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert me.status_code == 200

    # New refresh token should be different (rotation)
    assert new_refresh != original_refresh

    # Old refresh token should be revoked (cannot be used again)
    r = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert r.status_code == 401


def test_logout_revokes_token(api_client: TestClient):
    """Logout should revoke the refresh token."""
    # Login
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    refresh_token = r.json()["refresh_token"]
    access_token = r.json()["access_token"]

    # Logout
    r = api_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200

    # Try to refresh with revoked token
    r = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r.status_code == 401


def test_invalid_refresh_token_rejected(api_client: TestClient):
    """Invalid refresh token should be rejected."""
    r = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token-12345"},
    )
    assert r.status_code == 401


def test_admin_can_list_users(api_client: TestClient):
    """Admin should be able to list users (RBAC check)."""
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    access = r.json()["access_token"]

    users = api_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert users.status_code == 200
    data = users.json()
    assert "items" in data
    assert len(data["items"]) > 0
