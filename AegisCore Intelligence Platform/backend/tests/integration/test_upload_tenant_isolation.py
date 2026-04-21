"""Tests for tenant-aware data upload functionality.

Verifies that:
- CSV uploads are processed with correct tenant scoping
- Cross-tenant data insertion is blocked
- Validation errors are reported correctly
- Import summaries are accurate
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import rbac
from app.models.oltp import Asset, BusinessUnit, Organization, User, VulnerabilityFinding
from app.repositories.user_repository import UserRepository


def _create_org(db: Session, name: str, code: str) -> Organization:
    """Helper to create a test organization."""
    org = Organization(name=name, code=code, is_active=True, approval_status="approved")
    db.add(org)
    db.flush()
    return org


def _create_bu(db: Session, tenant_id: uuid.UUID, name: str, code: str) -> BusinessUnit:
    """Helper to create a test business unit."""
    bu = BusinessUnit(tenant_id=tenant_id, name=name, code=code)
    db.add(bu)
    db.flush()
    return bu


def _create_user(
    db: Session,
    tenant_id: uuid.UUID,
    email: str,
    full_name: str,
    password: str = "Password123!",
) -> User:
    """Helper to create a test user."""
    from app.core.security import hash_password
    
    user = User(
        tenant_id=tenant_id,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _assign_role(db: Session, user_id: uuid.UUID, role_name: str) -> None:
    """Helper to assign a role to a user."""
    repo = UserRepository(db)
    role = repo.get_role_by_name(role_name)
    if role:
        repo.add_role(user_id, role.id)
    db.commit()


def _make_csv_content(rows: list[dict]) -> bytes:
    """Helper to create CSV content from dict rows."""
    if not rows:
        return b""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


class TestAssetUpload:
    """Tests for asset CSV upload functionality."""

    def test_upload_assets_creates_records_in_tenant(
        self, api_client: TestClient, db: Session
    ):
        """Uploaded assets should be created in the user's tenant."""
        # Setup tenant
        tenant = _create_org(db, "Upload Test Tenant", "upload-tenant")
        bu = _create_bu(db, tenant.id, "Engineering", "eng")
        
        user = _create_user(db, tenant.id, "admin@upload.example.com", "Admin User")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        # Login
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "upload-tenant",
                "email": "admin@upload.example.com",
                "password": "Password123!",
            },
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        
        # Create CSV content
        csv_content = _make_csv_content([
            {
                "name": "Test Server",
                "asset_type": "server",
                "hostname": "test.example.com",
                "ip_address": "192.168.1.100",
                "business_unit_code": "eng",
                "criticality": "4",
            }
        ])
        
        # Upload
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("assets.csv", csv_content, "text/csv")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["summary"]["inserted"] == 1
        assert data["summary"]["failed"] == 0
        
        # Verify asset was created in correct tenant
        from sqlalchemy import select
        stmt = select(Asset).where(Asset.tenant_id == tenant.id)
        assets = db.execute(stmt).scalars().all()
        assert len(assets) == 1
        assert assets[0].name == "Test Server"
        assert assets[0].tenant_id == tenant.id

    def test_upload_validates_business_unit_in_same_tenant(
        self, api_client: TestClient, db: Session
    ):
        """Upload should fail if business unit doesn't exist in tenant."""
        # Create two tenants
        tenant_a = _create_org(db, "Tenant A Upload", "tenant-a-upload")
        tenant_b = _create_org(db, "Tenant B Upload", "tenant-b-upload")
        
        # BU only in tenant B
        _create_bu(db, tenant_b.id, "Sales", "sales")
        
        user = _create_user(db, tenant_a.id, "admin@a-upload.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        # Login
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "tenant-a-upload",
                "email": "admin@a-upload.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Try to use BU from other tenant
        csv_content = _make_csv_content([
            {
                "name": "Test Asset",
                "asset_type": "server",
                "business_unit_code": "sales",  # This BU is in tenant B
                "criticality": "3",
            }
        ])
        
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("assets.csv", csv_content, "text/csv")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False  # All rows failed
        assert data["summary"]["failed"] == 1
        assert "not found in this company" in data["summary"]["errors"][0]["message"]

    def test_upload_updates_existing_assets_by_hostname(
        self, api_client: TestClient, db: Session
    ):
        """Upload should update existing assets matched by hostname."""
        tenant = _create_org(db, "Update Test", "update-test")
        bu = _create_bu(db, tenant.id, "Engineering", "eng")
        
        # Create existing asset
        existing = Asset(
            tenant_id=tenant.id,
            name="Old Name",
            asset_type="server",
            hostname="web01.example.com",
            business_unit_id=bu.id,
            criticality=3,
        )
        db.add(existing)
        db.commit()
        
        user = _create_user(db, tenant.id, "admin@update.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        # Login
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "update-test",
                "email": "admin@update.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Upload with same hostname
        csv_content = _make_csv_content([
            {
                "name": "New Name",
                "asset_type": "web_server",
                "hostname": "web01.example.com",
                "business_unit_code": "eng",
                "criticality": "5",
            }
        ])
        
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("assets.csv", csv_content, "text/csv")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["updated"] == 1
        assert data["summary"]["inserted"] == 0
        
        # Verify update
        db.refresh(existing)
        assert existing.name == "New Name"
        assert existing.asset_type == "web_server"
        assert existing.criticality == 5

    def test_upload_validates_csv_format(self, api_client: TestClient, db: Session):
        """Upload should reject invalid CSV files."""
        tenant = _create_org(db, "CSV Test", "csv-test")
        _create_bu(db, tenant.id, "Engineering", "eng")
        
        user = _create_user(db, tenant.id, "admin@csv.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "csv-test",
                "email": "admin@csv.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Upload invalid content
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("assets.csv", b"not a valid csv", "text/csv")},
        )
        
        # Should fail gracefully
        assert response.status_code in [200, 400]


class TestVulnerabilityUpload:
    """Tests for vulnerability CSV upload functionality."""

    def test_upload_vulnerabilities_links_to_tenant_assets(
        self, api_client: TestClient, db: Session
    ):
        """Vulnerabilities should be linked to assets in the same tenant."""
        tenant = _create_org(db, "Vuln Test", "vuln-test")
        bu = _create_bu(db, tenant.id, "Engineering", "eng")
        
        # Create asset
        asset = Asset(
            tenant_id=tenant.id,
            name="Web Server",
            asset_type="server",
            hostname="web01.example.com",
            business_unit_id=bu.id,
            criticality=3,
        )
        db.add(asset)
        db.commit()
        
        user = _create_user(db, tenant.id, "admin@vuln.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        # Login
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "vuln-test",
                "email": "admin@vuln.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Upload vulnerability
        csv_content = _make_csv_content([
            {
                "cve_id": "CVE-2024-1234",
                "asset_identifier": "web01.example.com",
                "status": "OPEN",
                "discovered_date": "2024-01-15",
                "notes": "Critical vulnerability",
            }
        ])
        
        response = api_client.post(
            "/api/v1/upload/vulnerabilities",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("vulns.csv", csv_content, "text/csv")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["summary"]["inserted"] == 1
        
        # Verify finding was created
        from sqlalchemy import select
        from app.models.oltp import CveRecord
        
        stmt = select(VulnerabilityFinding).where(
            VulnerabilityFinding.tenant_id == tenant.id
        )
        findings = db.execute(stmt).scalars().all()
        assert len(findings) == 1
        assert findings[0].asset_id == asset.id

    def test_upload_fails_for_asset_in_other_tenant(
        self, api_client: TestClient, db: Session
    ):
        """Cannot create vulnerability for asset in another tenant."""
        tenant_a = _create_org(db, "Tenant A Vuln", "tenant-a-vuln")
        tenant_b = _create_org(db, "Tenant B Vuln", "tenant-b-vuln")
        
        bu_b = _create_bu(db, tenant_b.id, "Sales", "sales")
        
        # Asset only in tenant B
        asset_b = Asset(
            tenant_id=tenant_b.id,
            name="Sales Server",
            asset_type="server",
            hostname="sales.example.com",
            business_unit_id=bu_b.id,
            criticality=3,
        )
        db.add(asset_b)
        db.commit()
        
        user_a = _create_user(db, tenant_a.id, "admin@a-vuln.example.com", "Admin")
        _assign_role(db, user_a.id, rbac.ROLE_ADMIN)
        
        # Login as tenant A user
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "tenant-a-vuln",
                "email": "admin@a-vuln.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Try to create vulnerability for tenant B asset
        csv_content = _make_csv_content([
            {
                "cve_id": "CVE-2024-9999",
                "asset_identifier": "sales.example.com",
                "status": "OPEN",
            }
        ])
        
        response = api_client.post(
            "/api/v1/upload/vulnerabilities",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("vulns.csv", csv_content, "text/csv")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["failed"] == 1
        assert "Asset not found" in data["summary"]["errors"][0]["message"]

    def test_upload_validates_cve_format(self, api_client: TestClient, db: Session):
        """CVE IDs must be in valid format."""
        tenant = _create_org(db, "CVE Format Test", "cve-format-test")
        bu = _create_bu(db, tenant.id, "Eng", "eng")
        
        asset = Asset(
            tenant_id=tenant.id,
            name="Server",
            asset_type="server",
            hostname="srv.example.com",
            business_unit_id=bu.id,
            criticality=3,
        )
        db.add(asset)
        db.commit()
        
        user = _create_user(db, tenant.id, "admin@cve-format.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "cve-format-test",
                "email": "admin@cve-format.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Invalid CVE format
        csv_content = _make_csv_content([
            {
                "cve_id": "INVALID-CVE",
                "asset_identifier": "srv.example.com",
                "status": "OPEN",
            }
        ])
        
        response = api_client.post(
            "/api/v1/upload/vulnerabilities",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("vulns.csv", csv_content, "text/csv")},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["failed"] == 1
        assert "Invalid CVE ID format" in data["summary"]["errors"][0]["message"]


class TestUploadSecurity:
    """Security tests for upload functionality."""

    def test_upload_rejects_non_csv_files(self, api_client: TestClient, db: Session):
        """Only CSV files should be accepted."""
        tenant = _create_org(db, "Security Test", "security-test")
        _create_bu(db, tenant.id, "Eng", "eng")
        
        user = _create_user(db, tenant.id, "admin@security.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "security-test",
                "email": "admin@security.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Try to upload non-CSV
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("malicious.exe", b"malicious content", "application/octet-stream")},
        )
        
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_upload_respects_file_size_limit(
        self, api_client: TestClient, db: Session
    ):
        """Files larger than 10MB should be rejected."""
        tenant = _create_org(db, "Size Test", "size-test")
        _create_bu(db, tenant.id, "Eng", "eng")
        
        user = _create_user(db, tenant.id, "admin@size.example.com", "Admin")
        _assign_role(db, user.id, rbac.ROLE_ADMIN)
        
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "size-test",
                "email": "admin@size.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        # Create large file content (>10MB)
        large_content = b"x" * (11 * 1024 * 1024)
        
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("large.csv", large_content, "text/csv")},
        )
        
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_upload_requires_write_permissions(
        self, api_client: TestClient, db: Session
    ):
        """Only users with write permissions can upload."""
        tenant = _create_org(db, "Perm Test", "perm-test")
        _create_bu(db, tenant.id, "Eng", "eng")
        
        # Create user with only reader role
        user = _create_user(db, tenant.id, "reader@perm.example.com", "Reader")
        # Assign manager role (read-only)
        _assign_role(db, user.id, rbac.ROLE_MANAGER)
        
        login_res = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "perm-test",
                "email": "reader@perm.example.com",
                "password": "Password123!",
            },
        )
        token = login_res.json()["access_token"]
        
        csv_content = _make_csv_content([
            {
                "name": "Test",
                "asset_type": "server",
                "business_unit_code": "eng",
            }
        ])
        
        response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("assets.csv", csv_content, "text/csv")},
        )
        
        # Should be forbidden
        assert response.status_code == 403
