"""End-to-end tests for complete SaaS user journey.

These tests verify all four user flows work together:
1. New company onboarding
2. Company admin setup  
3. Daily usage
4. Platform owner flow
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.core import rbac
from app.models.oltp import (
    Asset,
    BusinessUnit,
    CveRecord,
    Organization,
    OrganizationInvitation,
    User,
    VulnerabilityFinding,
)
from app.models.email_verification import EmailVerification
from app.repositories.user_repository import UserRepository


def _make_csv(rows: list[dict]) -> bytes:
    """Create CSV content from dict rows."""
    if not rows:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


class TestFlow1_NewCompanyOnboarding:
    """Flow 1: New company registers, admin created, logs in, reaches dashboard."""

    def test_complete_onboarding_flow(self, api_client: TestClient, db: Session):
        """End-to-end test: register → login → dashboard access."""
        # Step 1: Register new company
        register_data = {
            "company_name": "TestCorp Inc",
            "company_code": "testcorp-e2e",
            "admin_email": "admin@testcorp-e2e.example.com",
            "admin_password": "SecurePass123!",
            "admin_full_name": "Test Admin",
        }
        
        response = api_client.post("/api/v1/auth/register-company", json=register_data)
        assert response.status_code == 201
        registration = response.json()
        assert registration.get("requires_verification") is True
        user_id = registration.get("user_id")
        assert user_id
        
        # Verify company created (auto-approved by default)
        from sqlalchemy import select
        org = db.execute(
            select(Organization).where(Organization.code == "testcorp-e2e")
        ).scalar_one_or_none()
        assert org is not None
        assert org.approval_status == "approved"
        
        # Step 2: Verify email before first login
        verification = db.query(EmailVerification).filter(
            EmailVerification.user_id == uuid.UUID(user_id)
        ).order_by(EmailVerification.created_at.desc()).first()
        assert verification is not None
        verify_response = api_client.post(
            "/api/v1/auth/verify-email",
            json={"user_id": user_id, "code": verification.code},
        )
        assert verify_response.status_code == 200

        # Step 3: Admin can log in after verification
        login_response = api_client.post("/api/v1/auth/login", json={
            "company_code": "testcorp-e2e",
            "email": "admin@testcorp-e2e.example.com",
            "password": "SecurePass123!",
        })
        assert login_response.status_code == 200
        admin_tokens = login_response.json()
        
        # Step 4: Verify /me returns correct tenant info
        me_response = api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["tenant_code"] == "testcorp-e2e"
        assert me_data["tenant_name"] == "TestCorp Inc"
        assert "admin" in me_data["roles"]
        
        # Step 5: Access dashboard data
        dashboard_response = api_client.get(
            "/api/v1/analytics/summary",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert dashboard_response.status_code == 200


class TestFlow2_CompanyAdminSetup:
    """Flow 2: Admin uploads data, invites users, users access tenant workspace."""

    def test_admin_setup_flow(self, api_client: TestClient, db: Session):
        """Complete admin setup: upload data → invite users → users login."""
        # Setup approved tenant
        from sqlalchemy import select
        
        org = Organization(
            name="SetupCorp",
            code="setupcorp-e2e",
            is_active=True,
            approval_status="approved",
        )
        db.add(org)
        db.flush()
        
        # Create business unit
        bu = BusinessUnit(tenant_id=org.id, name="Engineering", code="eng")
        db.add(bu)
        db.flush()
        
        # Create admin
        from app.core.security import hash_password
        admin = User(
            tenant_id=org.id,
            email="admin@setupcorp-e2e.example.com",
            full_name="Setup Admin",
            hashed_password=hash_password("AdminPass123!"),
            is_active=True,
        )
        db.add(admin)
        db.flush()
        
        # Assign admin role
        repo = UserRepository(db)
        admin_role = repo.get_role_by_name(rbac.ROLE_ADMIN)
        repo.add_role(admin.id, admin_role.id)
        db.commit()
        
        # Step 1: Admin logs in
        login = api_client.post("/api/v1/auth/login", json={
            "company_code": "setupcorp-e2e",
            "email": "admin@setupcorp-e2e.example.com",
            "password": "AdminPass123!",
        })
        admin_token = login.json()["access_token"]
        
        # Step 2: Upload assets CSV
        assets_csv = _make_csv([
            {
                "name": "Production Server",
                "asset_type": "server",
                "hostname": "prod01.setupcorp.example.com",
                "ip_address": "10.0.1.10",
                "business_unit_code": "eng",
                "criticality": "5",
            },
            {
                "name": "Database Server",
                "asset_type": "database",
                "hostname": "db01.setupcorp.example.com",
                "ip_address": "10.0.1.20",
                "business_unit_code": "eng",
                "criticality": "5",
            },
        ])
        
        upload_response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("assets.csv", assets_csv, "text/csv")},
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        assert upload_data["success"] is True
        assert upload_data["summary"]["inserted"] == 2
        
        # Verify assets in DB with correct tenant
        assets = db.execute(
            select(Asset).where(Asset.tenant_id == org.id)
        ).scalars().all()
        assert len(assets) == 2
        
        # Step 3: Upload vulnerabilities
        vuln_csv = _make_csv([
            {
                "cve_id": "CVE-2024-0001",
                "asset_identifier": "prod01.setupcorp.example.com",
                "status": "OPEN",
                "discovered_date": "2024-01-15",
                "notes": "Critical test vulnerability",
            },
        ])
        
        vuln_response = api_client.post(
            "/api/v1/upload/vulnerabilities",
            headers={"Authorization": f"Bearer {admin_token}"},
            files={"file": ("vulns.csv", vuln_csv, "text/csv")},
        )
        assert vuln_response.status_code == 200
        vuln_data = vuln_response.json()
        assert vuln_data["summary"]["inserted"] == 1
        
        # Step 4: Invite analyst user
        invite_response = api_client.post(
            "/api/v1/users/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "analyst@setupcorp-e2e.example.com",
                "role_name": "analyst",
                "expires_in_hours": 168,
            },
        )
        assert invite_response.status_code == 201
        invite_data = invite_response.json()
        invitation_token = invite_data["invitation_token"]
        
        # Verify invitation created in DB
        invitation = db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.email == "analyst@setupcorp-e2e.example.com"
            )
        ).scalar_one_or_none()
        assert invitation is not None
        assert invitation.tenant_id == org.id
        
        # Step 5: Analyst accepts invitation
        accept_response = api_client.post("/api/v1/auth/accept-invitation", json={
            "invitation_token": invitation_token,
            "full_name": "Test Analyst",
            "password": "AnalystPass123!",
        })
        assert accept_response.status_code == 200
        
        # Step 6: Analyst logs in
        analyst_login = api_client.post("/api/v1/auth/login", json={
            "company_code": "setupcorp-e2e",
            "email": "analyst@setupcorp-e2e.example.com",
            "password": "AnalystPass123!",
        })
        assert analyst_login.status_code == 200
        analyst_token = analyst_login.json()["access_token"]
        
        # Step 7: Analyst accesses tenant-only data
        me_response = api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["tenant_code"] == "setupcorp-e2e"
        assert "analyst" in me_data["roles"]
        
        # Step 8: Analyst can view assets
        assets_response = api_client.get(
            "/api/v1/assets",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert assets_response.status_code == 200
        assets_data = assets_response.json()
        assert assets_data["total"] == 2  # Both assets visible
        
        # Step 9: Analyst can view vulnerabilities
        findings_response = api_client.get(
            "/api/v1/findings",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert findings_response.status_code == 200
        findings_data = findings_response.json()
        assert findings_data["total"] == 1


class TestFlow3_DailyUsage:
    """Flow 3: Analyst checks vulnerabilities, manager runs simulation, team uses search."""

    def test_daily_usage_flow(self, api_client: TestClient, db: Session):
        """Daily operations: prioritize, simulate, search, dashboard."""
        from sqlalchemy import select
        
        # Setup tenant with data
        org = Organization(
            name="DailyCorp",
            code="dailycorp-e2e",
            is_active=True,
            approval_status="approved",
        )
        db.add(org)
        db.flush()
        
        bu = BusinessUnit(tenant_id=org.id, name="Engineering", code="eng")
        db.add(bu)
        db.flush()
        
        # Create assets
        asset1 = Asset(
            tenant_id=org.id,
            name="Critical Server",
            asset_type="server",
            hostname="critical.dailycorp.example.com",
            business_unit_id=bu.id,
            criticality=5,
        )
        asset2 = Asset(
            tenant_id=org.id,
            name="Standard Server",
            asset_type="server",
            hostname="standard.dailycorp.example.com",
            business_unit_id=bu.id,
            criticality=3,
        )
        db.add_all([asset1, asset2])
        db.flush()
        
        # Create CVE records
        from app.models.oltp import CveRecord
        cve1 = CveRecord(cve_id="CVE-2024-CRITICAL", title="Critical Vuln", severity="CRITICAL")
        cve2 = CveRecord(cve_id="CVE-2024-HIGH", title="High Vuln", severity="HIGH")
        db.add_all([cve1, cve2])
        db.flush()
        
        # Create vulnerabilities
        finding1 = VulnerabilityFinding(
            tenant_id=org.id,
            asset_id=asset1.id,
            cve_record_id=cve1.id,
            status="OPEN",
            discovered_at=datetime.now(timezone.utc),
        )
        finding2 = VulnerabilityFinding(
            tenant_id=org.id,
            asset_id=asset2.id,
            cve_record_id=cve2.id,
            status="OPEN",
            discovered_at=datetime.now(timezone.utc),
        )
        db.add_all([finding1, finding2])
        db.commit()
        
        # Create users
        from app.core.security import hash_password
        
        analyst = User(
            tenant_id=org.id,
            email="analyst@dailycorp-e2e.example.com",
            full_name="Daily Analyst",
            hashed_password=hash_password("DailyPass123!"),
            is_active=True,
        )
        manager = User(
            tenant_id=org.id,
            email="manager@dailycorp-e2e.example.com",
            full_name="Daily Manager",
            hashed_password=hash_password("DailyPass123!"),
            is_active=True,
        )
        db.add_all([analyst, manager])
        db.flush()
        
        # Assign roles
        repo = UserRepository(db)
        analyst_role = repo.get_role_by_name(rbac.ROLE_ANALYST)
        manager_role = repo.get_role_by_name(rbac.ROLE_MANAGER)
        repo.add_role(analyst.id, analyst_role.id)
        repo.add_role(manager.id, manager_role.id)
        db.commit()
        
        # Login as analyst
        analyst_login = api_client.post("/api/v1/auth/login", json={
            "company_code": "dailycorp-e2e",
            "email": "analyst@dailycorp-e2e.example.com",
            "password": "DailyPass123!",
        })
        analyst_token = analyst_login.json()["access_token"]
        
        # Step 1: Analyst checks prioritized vulnerabilities
        prioritize_response = api_client.get(
            "/api/v1/prioritization/vulnerabilities",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert prioritize_response.status_code == 200
        
        # Step 2: Analyst searches for vulnerabilities
        search_response = api_client.get(
            "/api/v1/findings?search=CVE-2024",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["total"] == 2  # Both vulnerabilities found
        
        # Step 3: Manager views dashboard analytics
        manager_login = api_client.post("/api/v1/auth/login", json={
            "company_code": "dailycorp-e2e",
            "email": "manager@dailycorp-e2e.example.com",
            "password": "DailyPass123!",
        })
        manager_token = manager_login.json()["access_token"]
        
        dashboard_response = api_client.get(
            "/api/v1/analytics/summary",
            headers={"Authorization": f"Bearer {manager_token}"},
        )
        assert dashboard_response.status_code == 200
        
        # Step 4: Analyst runs simulation (requires WriterDep)
        sim_response = api_client.post(
            "/api/v1/simulate/remediation",
            headers={"Authorization": f"Bearer {analyst_token}"},
            json={"finding_ids": [str(finding1.id)], "scenario_name": "Test patch scenario"},
        )
        assert sim_response.status_code == 200


class TestFlow4_PlatformOwnerFlow:
    """Flow 4: Platform owner manages companies, monitors platform safely."""

    def test_platform_owner_flow(self, api_client: TestClient, db: Session):
        """Platform owner manages companies and monitors usage."""
        from sqlalchemy import select
        
        # Create multiple companies
        companies = []
        for i in range(3):
            org = Organization(
                name=f"TenantCorp {i+1}",
                code=f"tenantcorp{i+1}-e2e",
                is_active=True,
                approval_status="pending" if i == 2 else "approved",
            )
            db.add(org)
            db.flush()
            companies.append(org)
            
            # Add some users to each
            from app.core.security import hash_password
            user = User(
                tenant_id=org.id,
                email=f"admin{i}@tenantcorp{i+1}-e2e.example.com",
                full_name=f"Admin {i+1}",
                hashed_password=hash_password("TestPass123!"),
                is_active=True,
            )
            db.add(user)
        db.commit()
        
        # Create platform owner and aegiscore org within the test transaction
        from app.core.security import hash_password
        from app.repositories.user_repository import UserRepository
        from app.core import rbac as rbac_module

        # Create aegiscore organization (use hardcoded UUID)
        aegiscore_id = uuid.UUID("a0000000-0000-4000-8000-000000000002")
        aegiscore_org = db.execute(
            sa_select(Organization).where(Organization.code == "aegiscore")
        ).scalar_one_or_none()
        assert aegiscore_org is not None

        # Ensure platform owner user exists
        from app.models.oltp import UserRole
        platform_owner = db.execute(
            sa_select(User).where(User.email == "platform@aegiscore.local")
        ).scalar_one_or_none()
        if platform_owner is None:
            platform_owner = User(
                id=uuid.uuid4(),
                tenant_id=aegiscore_id,
                email="platform@aegiscore.local",
                hashed_password=hash_password("platform123"),
                full_name="Platform Owner",
                is_active=True,
            )
            db.add(platform_owner)
            db.flush()

        # Get platform_owner role and assign
        repo = UserRepository(db)
        po_role = repo.get_role_by_name(rbac_module.ROLE_PLATFORM_OWNER)
        if po_role:
            existing_user_role = db.execute(
                sa_select(UserRole).where(
                    UserRole.user_id == platform_owner.id,
                    UserRole.role_id == po_role.id,
                )
            ).scalar_one_or_none()
            if existing_user_role is None:
                user_role = UserRole(user_id=platform_owner.id, role_id=po_role.id)
                db.add(user_role)
                db.flush()

        # Login as platform owner
        po_login = api_client.post("/api/v1/auth/login", json={
            "company_code": "aegiscore",
            "email": "platform@aegiscore.local",
            "password": "platform123",
        })
        assert po_login.status_code == 200
        po_token = po_login.json()["access_token"]
        
        # Step 1: List all tenants
        tenants_response = api_client.get(
            "/api/v1/platform/tenants",
            headers={"Authorization": f"Bearer {po_token}"},
        )
        assert tenants_response.status_code == 200
        tenants_data = tenants_response.json()
        assert len(tenants_data["items"]) >= 3
        
        # Step 2: View platform statistics
        stats_response = api_client.get(
            "/api/v1/platform/stats",
            headers={"Authorization": f"Bearer {po_token}"},
        )
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert "total_tenants" in stats_data
        
        # Step 3: View pending approvals
        pending_response = api_client.get(
            "/api/v1/platform/tenants?approval_status=pending",
            headers={"Authorization": f"Bearer {po_token}"},
        )
        assert pending_response.status_code == 200
        pending_data = pending_response.json()
        assert any(t["approval_status"] == "pending" for t in pending_data["items"])
        
        # Step 4: Approve pending company
        pending_company = companies[2]  # The pending one
        approve_response = api_client.patch(
            f"/api/v1/platform/tenants/{pending_company.id}",
            headers={"Authorization": f"Bearer {po_token}"},
            json={
                "approval_status": "approved",
                "approval_notes": "Approved via E2E test",
            },
        )
        assert approve_response.status_code == 200
        
        # Verify tenant status updated in DB
        db.refresh(pending_company)
        assert pending_company.approval_status == "approved"
        
        # Step 5: Suspend a company
        suspend_response = api_client.patch(
            f"/api/v1/platform/tenants/{companies[0].id}",
            headers={"Authorization": f"Bearer {po_token}"},
            json={
                "is_active": False,
                "approval_notes": "Suspended for testing",
            },
        )
        assert suspend_response.status_code == 200
        
        # Verify company is now inactive
        db.refresh(companies[0])
        assert companies[0].is_active is False
        
        # Step 6: Verify company users cannot log in to suspended company
        suspended_login = api_client.post("/api/v1/auth/login", json={
            "company_code": companies[0].code,
            "email": f"admin0@tenantcorp1-e2e.example.com",
            "password": "TestPass123!",
        })
        assert suspended_login.status_code == 401  # Cannot login to inactive company


class TestCrossFlowSecurity:
    """Security tests across all flows."""

    def test_user_cannot_access_other_tenant_data_in_any_flow(
        self, api_client: TestClient, db: Session
    ):
        """Cross-tenant access blocked in all scenarios."""
        from sqlalchemy import select
        
        # Create two companies with data
        org_a = Organization(
            name="Company A Security",
            code="company-a-sec",
            is_active=True,
            approval_status="approved",
        )
        org_b = Organization(
            name="Company B Security",
            code="company-b-sec",
            is_active=True,
            approval_status="approved",
        )
        db.add_all([org_a, org_b])
        db.flush()
        
        # Add business units
        bu_a = BusinessUnit(tenant_id=org_a.id, name="Eng A", code="eng-a")
        bu_b = BusinessUnit(tenant_id=org_b.id, name="Eng B", code="eng-b")
        db.add_all([bu_a, bu_b])
        db.flush()
        
        # Create users
        from app.core.security import hash_password
        
        user_a = User(
            tenant_id=org_a.id,
            email="user@company-a-sec.example.com",
            full_name="User A",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
        )
        user_b = User(
            tenant_id=org_b.id,
            email="user@company-b-sec.example.com",
            full_name="User B",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
        )
        db.add_all([user_a, user_b])
        db.flush()
        
        # Assign roles
        repo = UserRepository(db)
        role = repo.get_role_by_name(rbac.ROLE_ADMIN)
        repo.add_role(user_a.id, role.id)
        repo.add_role(user_b.id, role.id)
        db.commit()
        
        # Create asset in company B
        asset_b = Asset(
            tenant_id=org_b.id,
            name="Secret Server",
            asset_type="server",
            hostname="secret.company-b-sec.example.com",
            business_unit_id=bu_b.id,
            criticality=5,
        )
        db.add(asset_b)
        db.commit()
        
        # User A logs in
        login_a = api_client.post("/api/v1/auth/login", json={
            "company_code": "company-a-sec",
            "email": "user@company-a-sec.example.com",
            "password": "Pass123!",
        })
        token_a = login_a.json()["access_token"]
        
        # User A tries to access asset from company B (direct ID)
        asset_response = api_client.get(
            f"/api/v1/assets/{asset_b.id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        # Should return 404 (not 403) to avoid leaking existence
        assert asset_response.status_code == 404
        
        # User A tries to list assets from company B (should only see own)
        list_response = api_client.get(
            "/api/v1/assets",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert list_data["total"] == 0  # No assets in company A

    def test_data_upload_isolation(self, api_client: TestClient, db: Session):
        """Uploaded data is strictly isolated to uploader's tenant."""
        from sqlalchemy import select
        
        # Create two companies
        org_a = Organization(
            name="Upload A",
            code="upload-a",
            is_active=True,
            approval_status="approved",
        )
        org_b = Organization(
            name="Upload B",
            code="upload-b",
            is_active=True,
            approval_status="approved",
        )
        db.add_all([org_a, org_b])
        db.flush()
        
        # Business unit only in B
        bu_b = BusinessUnit(tenant_id=org_b.id, name="Sales B", code="sales-b")
        db.add(bu_b)
        db.commit()
        
        # Create admin in company A
        from app.core.security import hash_password
        admin_a = User(
            tenant_id=org_a.id,
            email="admin@upload-a.example.com",
            full_name="Admin A",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
        )
        db.add(admin_a)
        db.flush()
        
        repo = UserRepository(db)
        role = repo.get_role_by_name(rbac.ROLE_ADMIN)
        repo.add_role(admin_a.id, role.id)
        db.commit()
        
        # Admin A logs in
        login = api_client.post("/api/v1/auth/login", json={
            "company_code": "upload-a",
            "email": "admin@upload-a.example.com",
            "password": "Pass123!",
        })
        token_a = login.json()["access_token"]
        
        # Admin A tries to use business unit from company B
        csv_content = _make_csv([
            {
                "name": "Hacked Asset",
                "asset_type": "server",
                "business_unit_code": "sales-b",  # BU from company B
                "criticality": "5",
            }
        ])
        
        upload_response = api_client.post(
            "/api/v1/upload/assets",
            headers={"Authorization": f"Bearer {token_a}"},
            files={"file": ("assets.csv", csv_content, "text/csv")},
        )
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        # Should fail because BU doesn't exist in company A
        assert upload_data["summary"]["failed"] == 1
        assert "not found in this company" in upload_data["summary"]["errors"][0]["message"]
        
        # Verify no asset was created
        assets = db.execute(
            select(Asset).where(Asset.tenant_id == org_a.id)
        ).scalars().all()
        assert len(assets) == 0
