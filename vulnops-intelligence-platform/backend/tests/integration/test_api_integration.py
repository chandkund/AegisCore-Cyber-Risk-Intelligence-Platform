"""Full-stack API checks against a real PostgreSQL (migrated + seeded).

Set `VULNOPS_TEST_DATABASE_URL` (e.g. same as local `DATABASE_URL`) to enable.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration


def _skip_if_no_db() -> str:
    url = os.getenv("VULNOPS_TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("VULNOPS_TEST_DATABASE_URL not set")
    try:
        eng = create_engine(url.replace("postgresql+asyncpg", "postgresql+psycopg", 1))
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        eng.dispose()
    except Exception:
        pytest.skip("VULNOPS_TEST_DATABASE_URL unreachable")
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
        json={"email": "analyst@vulnops.local", "password": "VulnOps!demo2026"},
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
        json={"email": "manager@vulnops.local", "password": "VulnOps!demo2026"},
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
