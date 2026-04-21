from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_liveness_does_not_touch_database():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
