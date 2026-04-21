"""Finding CRUD integration tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _get_analyst_client(api_client: TestClient) -> str:
    """Login as analyst and return access token."""
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def _get_or_create_asset(api_client: TestClient, token: str) -> str:
    """Get first asset or create one for testing."""
    r = api_client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = r.json()
    if data["items"]:
        return data["items"][0]["id"]

    # Create if none exist
    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Test Asset for Finding",
            "asset_type": "server",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",
            "criticality": 3,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.json()["id"]

def _get_or_create_cve_id(api_client: TestClient, token: str, db: Session) -> str:
    """Return an existing CVE id or create one in test DB."""
    r = api_client.get(
        "/api/v1/cve-records?limit=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    if data["items"]:
        return data["items"][0]["cve_id"]

    from app.models.oltp import CveRecord

    cve = CveRecord(
        cve_id="CVE-2024-50001",
        severity="HIGH",
        cvss_base_score=8.1,
        exploit_available=False,
        title="Test CVE for finding CRUD",
    )
    db.add(cve)
    db.commit()
    return cve.cve_id


def test_create_finding(api_client: TestClient, db: Session):
    """Create finding with valid data."""
    token = _get_analyst_client(api_client)
    asset_id = _get_or_create_asset(api_client, token)
    cve_id = _get_or_create_cve_id(api_client, token, db)

    r = api_client.post(
        "/api/v1/findings",
        json={
            "asset_id": asset_id,
            "cve_id": cve_id,
            "status": "OPEN",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "notes": "Test finding from integration test",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["asset_id"] == asset_id
    assert data["status"] == "OPEN"
    assert data["id"] is not None


def test_list_findings(api_client: TestClient):
    """List findings returns paginated results."""
    token = _get_analyst_client(api_client)

    r = api_client.get(
        "/api/v1/findings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data


def test_get_finding_by_id(api_client: TestClient, db: Session):
    """Get finding by ID."""
    token = _get_analyst_client(api_client)
    asset_id = _get_or_create_asset(api_client, token)
    cve_id = _get_or_create_cve_id(api_client, token, db)

    # Create finding
    r = api_client.post(
        "/api/v1/findings",
        json={
            "asset_id": asset_id,
            "cve_id": cve_id,
            "status": "OPEN",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    finding_id = r.json()["id"]

    # Get finding
    r = api_client.get(
        f"/api/v1/findings/{finding_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == finding_id
    assert data["cve_id"] == cve_id


def test_update_finding(api_client: TestClient, db: Session):
    """Update finding status."""
    token = _get_analyst_client(api_client)
    asset_id = _get_or_create_asset(api_client, token)
    cve_id = _get_or_create_cve_id(api_client, token, db)

    # Create
    r = api_client.post(
        "/api/v1/findings",
        json={
            "asset_id": asset_id,
            "cve_id": cve_id,
            "status": "OPEN",
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    finding_id = r.json()["id"]

    # Update
    r = api_client.patch(
        f"/api/v1/findings/{finding_id}",
        json={
            "status": "REMEDIATED",
            "notes": "Fixed and verified",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "REMEDIATED"
    assert data["notes"] == "Fixed and verified"


def test_filter_findings_by_status(api_client: TestClient):
    """Filter findings by status."""
    token = _get_analyst_client(api_client)

    r = api_client.get(
        "/api/v1/findings?status=OPEN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    # All returned items should have status OPEN
    for item in data["items"]:
        assert item["status"] == "OPEN"


def test_filter_findings_by_asset(api_client: TestClient):
    """Filter findings by asset_id."""
    token = _get_analyst_client(api_client)
    asset_id = _get_or_create_asset(api_client, token)

    r = api_client.get(
        f"/api/v1/findings?asset_id={asset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    # All returned items should belong to the asset
    for item in data["items"]:
        assert item["asset_id"] == asset_id


def test_pagination_findings(api_client: TestClient):
    """Test findings pagination."""
    token = _get_analyst_client(api_client)

    r = api_client.get(
        "/api/v1/findings?limit=5&offset=0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["limit"] == 5
    assert len(data["items"]) <= 5


def test_get_nonexistent_finding_returns_404(api_client: TestClient):
    """Get non-existent finding returns 404."""
    token = _get_analyst_client(api_client)

    r = api_client.get(
        "/api/v1/findings/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_create_finding_invalid_asset(api_client: TestClient):
    """Create finding with invalid asset_id should fail."""
    token = _get_analyst_client(api_client)

    r = api_client.post(
        "/api/v1/findings",
        json={
            "asset_id": "invalid-uuid",
            "cve_id": "CVE-2024-12345",
            "status": "OPEN",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_manager_can_view_findings(api_client: TestClient):
    """Manager role should be able to view findings (Reader permission)."""
    # Login as manager
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "manager@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Should be able to list findings
    r = api_client.get(
        "/api/v1/findings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
