"""Asset CRUD integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _get_admin_client(api_client: TestClient) -> str:
    """Login as admin and return access token."""
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def test_create_asset(api_client: TestClient):
    """Create asset with valid data."""
    token = _get_admin_client(api_client)

    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Test Server",
            "asset_type": "server",
            "hostname": "test-server-01",
            "ip_address": "192.168.1.100",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",  # Engineering
            "criticality": 4,
            "owner_email": "owner@example.com",
            "is_active": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Server"
    assert data["asset_type"] == "server"
    assert data["id"] is not None


def test_list_assets(api_client: TestClient):
    """List assets returns paginated results."""
    token = _get_admin_client(api_client)

    r = api_client.get(
        "/api/v1/assets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_get_asset_by_id(api_client: TestClient):
    """Get asset by ID."""
    token = _get_admin_client(api_client)

    # First create an asset
    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Get Test Asset",
            "asset_type": "workstation",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",
            "criticality": 3,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    asset_id = r.json()["id"]

    # Get the asset
    r = api_client.get(
        f"/api/v1/assets/{asset_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == asset_id
    assert data["name"] == "Get Test Asset"


def test_update_asset(api_client: TestClient):
    """Update asset fields."""
    token = _get_admin_client(api_client)

    # Create asset
    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Update Test Asset",
            "asset_type": "server",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",
            "criticality": 2,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    asset_id = r.json()["id"]

    # Update
    r = api_client.patch(
        f"/api/v1/assets/{asset_id}",
        json={
            "name": "Updated Asset Name",
            "criticality": 5,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Updated Asset Name"
    assert data["criticality"] == 5


def test_deactivate_asset(api_client: TestClient):
    """Deactivate asset via patch (hard delete not supported)."""
    token = _get_admin_client(api_client)

    # Create asset
    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Delete Test Asset",
            "asset_type": "server",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",
            "criticality": 3,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    asset_id = r.json()["id"]

    # Deactivate
    r = api_client.patch(
        f"/api/v1/assets/{asset_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_create_asset_invalid_criticality(api_client: TestClient):
    """Asset creation with invalid criticality should fail."""
    token = _get_admin_client(api_client)

    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Invalid Asset",
            "asset_type": "server",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",
            "criticality": 10,  # Invalid: must be 1-5
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_get_nonexistent_asset_returns_404(api_client: TestClient):
    """Get non-existent asset returns 404."""
    token = _get_admin_client(api_client)

    r = api_client.get(
        "/api/v1/assets/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_manager_cannot_create_asset(api_client: TestClient):
    """Manager role should not be able to create assets (Writer role required)."""
    # Login as manager
    r = api_client.post(
        "/api/v1/auth/login",
        json={"email": "manager@aegiscore.local", "password": "AegisCore!demo2026"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]

    # Try to create asset
    r = api_client.post(
        "/api/v1/assets",
        json={
            "name": "Manager Asset",
            "asset_type": "server",
            "business_unit_id": "a5000001-0000-4000-8000-000000000010",
            "criticality": 3,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
