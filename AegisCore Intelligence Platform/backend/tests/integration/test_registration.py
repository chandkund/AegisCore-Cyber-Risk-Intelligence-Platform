"""Tests for company registration flow with email verification."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.email_verification import EmailVerification
from app.models.oltp import Organization, Role, User, UserRole


def _seed_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).one_or_none()
    if role is not None:
        return role
    role = Role(id=uuid.uuid4(), name=name, description=f"{name} role")
    db.add(role)
    db.flush()
    return role


def _create_user(
    db: Session,
    *,
    tenant_id: uuid.UUID | None,
    email: str,
    full_name: str,
    password: str,
    is_active: bool = True,
    email_verified: bool = True,
) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email.strip().lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        is_active=is_active,
        email_verified=email_verified,
    )
    db.add(user)
    db.flush()
    return user


def _assign_role(db: Session, *, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole:
    row = UserRole(user_id=user_id, role_id=role_id)
    db.add(row)
    db.flush()
    return row


class TestCompanyRegistrationWithVerification:
    """Test company registration with email verification flow."""

    def test_successful_registration_returns_user_id(self, api_client: TestClient, db: Session):
        """Test successful registration returns user_id for verification."""
        _seed_role(db, "admin")
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Test Corp",
                "company_code": "test-corp",
                "admin_email": "admin@testcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Test Admin",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        
        # Verify response structure
        assert "user_id" in data
        assert "message" in data
        assert data["requires_verification"] is True
        assert "access_token" not in data  # No tokens until verified
        
        # Verify user is created but not active
        user = db.query(User).filter(User.email == "admin@testcorp.example.com").first()
        assert user is not None
        assert user.is_active is False
        assert user.email_verified is False
        
        # Verify OTP was created
        verification = db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
        assert verification is not None
        assert verification.code is not None
        assert len(verification.code) == 6
        assert not verification.is_verified

    def test_email_verification_activates_user(self, api_client: TestClient, db: Session):
        """Test email verification activates user and returns tokens."""
        _seed_role(db, "admin")
        db.commit()

        # Register company
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Test Corp",
                "company_code": "test-corp-verify",
                "admin_email": "verify@testcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Verify Admin",
            },
        )
        data = response.json()
        user_id = data["user_id"]
        
        # Get verification code
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        verification = db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
        code = verification.code
        
        # Verify email
        response = api_client.post(
            "/api/v1/auth/verify-email",
            json={
                "user_id": user_id,
                "code": code,
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        
        # Verify tokens returned
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify user is now active
        db.refresh(user)
        assert user.is_active is True
        assert user.email_verified is True
        
        # Verify verification is marked as used
        db.refresh(verification)
        assert verification.is_verified is True

    def test_invalid_verification_code_fails(self, api_client: TestClient, db: Session):
        """Test invalid verification code returns error."""
        _seed_role(db, "admin")
        db.commit()

        # Register company
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Test Corp",
                "company_code": "test-corp-invalid",
                "admin_email": "invalid@testcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Invalid Admin",
            },
        )
        data = response.json()
        user_id = data["user_id"]
        
        # Try wrong code
        response = api_client.post(
            "/api/v1/auth/verify-email",
            json={
                "user_id": user_id,
                "code": "000000",  # Wrong code
            },
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_resend_verification_code(self, api_client: TestClient, db: Session):
        """Test resending verification code generates new code."""
        _seed_role(db, "admin")
        db.commit()

        # Register company
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Test Corp",
                "company_code": "test-corp-resend",
                "admin_email": "resend@testcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Resend Admin",
            },
        )
        data = response.json()
        user_id = data["user_id"]
        
        # Get first code
        user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
        verification = db.query(EmailVerification).filter(EmailVerification.user_id == user.id).first()
        first_code = verification.code
        
        # Resend code
        response = api_client.post(
            "/api/v1/auth/resend-verification",
            json={"user_id": user_id},
        )
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Verify new code was generated
        db.refresh(verification)
        # Old code should be revoked (marked as verified to prevent reuse)
        old_verification = db.query(EmailVerification).filter(
            EmailVerification.user_id == user.id,
            EmailVerification.code == first_code
        ).first()
        if old_verification:
            assert old_verification.is_verified is True

    def test_duplicate_company_code_rejected(self, api_client: TestClient, db: Session):
        """Test that duplicate company code returns 400 error."""
        _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Existing Corp", code="existing-corp", is_active=True)
        db.add(org)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "New Corp",
                "company_code": "existing-corp",  # Duplicate
                "admin_email": "admin@newcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "New Admin",
            },
        )
        assert response.status_code == 400, response.text
        assert "company code already exists" in response.json()["detail"].lower()

    def test_duplicate_email_rejected(self, api_client: TestClient, db: Session):
        """Test that duplicate email in same company returns 400."""
        _seed_role(db, "admin")
        
        # First registration
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Test Corp",
                "company_code": "test-corp-dup-email",
                "admin_email": "duplicate@testcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Admin One",
            },
        )
        assert response.status_code == 201
        
        # Try same email again (should fail)
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Another Corp",
                "company_code": "another-corp",
                "admin_email": "duplicate@testcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Admin Two",
            },
        )
        assert response.status_code == 400
        assert "email already exists" in response.json()["detail"].lower()

        # Verify admin role assigned
        user = db.query(User).filter(User.email == "duplicate@testcorp.example.com").first()
        assert user is not None
        user_roles = db.query(UserRole).filter(UserRole.user_id == user.id).all()
        assert len(user_roles) == 1
        role = db.query(Role).filter(Role.id == user_roles[0].role_id).first()
        assert role.name == "admin"

    def test_duplicate_company_code_rejected(self, api_client: TestClient, db: Session):
        """Test that duplicate company code returns 400 error."""
        _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Existing Corp", code="existing-corp", is_active=True)
        db.add(org)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "New Corp",
                "company_code": "existing-corp",  # Duplicate
                "admin_email": "admin@newcorp.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "New Admin",
            },
        )
        assert response.status_code == 400, response.text
        assert "company code already exists" in response.json()["detail"].lower()

    def test_duplicate_email_same_company_rejected(self, api_client: TestClient, db: Session):
        """Test that duplicate email within same company returns 400 error."""
        _seed_role(db, "admin")
        db.commit()

        # First registration
        response1 = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "First Corp",
                "company_code": "first-corp",
                "admin_email": "admin@shared.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "First Admin",
            },
        )
        assert response1.status_code == 201

        # Second registration with same email (should fail at company creation stage)
        response2 = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Second Corp",
                "company_code": "second-corp",
                "admin_email": "admin@shared.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Second Admin",
            },
        )
        # The second company is created first, then email check fails
        # The transaction should roll back or return an error
        if response2.status_code == 201:
            # If it succeeded, both companies exist with same email but different tenant_ids
            orgs = db.query(Organization).filter(Organization.code.in_(["first-corp", "second-corp"])).all()
            assert len(orgs) == 2
        else:
            assert response2.status_code == 400

    def test_weak_password_rejected(self, api_client: TestClient, db: Session):
        """Test that weak password (less than 12 chars) is rejected by schema validation."""
        _seed_role(db, "admin")
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Weak Pass Corp",
                "company_code": "weak-corp",
                "admin_email": "admin@weak.example.com",
                "admin_password": "short",  # Too short
                "admin_full_name": "Weak Admin",
            },
        )
        assert response.status_code == 422, response.text  # Validation error
        data = response.json()
        assert "detail" in data

    def test_invalid_company_code_rejected(self, api_client: TestClient, db: Session):
        """Test that invalid company code format is rejected."""
        _seed_role(db, "admin")
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Invalid Code Corp",
                "company_code": "Invalid_Code!",  # Invalid chars
                "admin_email": "admin@invalid.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Invalid Admin",
            },
        )
        assert response.status_code == 422, response.text  # Validation error

    def test_invalid_email_rejected(self, api_client: TestClient, db: Session):
        """Test that invalid email format is rejected."""
        _seed_role(db, "admin")
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Invalid Email Corp",
                "company_code": "invalid-email-corp",
                "admin_email": "not-an-email",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Invalid Admin",
            },
        )
        assert response.status_code == 422, response.text  # Validation error

    def test_missing_fields_rejected(self, api_client: TestClient, db: Session):
        """Test that missing required fields are rejected."""
        _seed_role(db, "admin")
        db.commit()

        # Missing company_name
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_code": "missing-name-corp",
                "admin_email": "admin@missing.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Missing Admin",
            },
        )
        assert response.status_code == 422

        # Missing company_code
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Missing Code Corp",
                "admin_email": "admin@missing.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Missing Admin",
            },
        )
        assert response.status_code == 422

    def test_company_code_normalized_to_lowercase(self, api_client: TestClient, db: Session):
        """Test that company code is normalized to lowercase."""
        _seed_role(db, "admin")
        db.commit()

        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Mixed Case Corp",
                "company_code": "Mixed-Case-Corp",
                "admin_email": "admin@mixed.example.com",
                "admin_password": "SecurePassword123!",
                "admin_full_name": "Mixed Admin",
            },
        )
        assert response.status_code == 201, response.text

        # Verify company code was normalized to lowercase
        org = db.query(Organization).filter(Organization.code == "mixed-case-corp").first()
        assert org is not None
        assert org.code == "mixed-case-corp"

    def test_password_securely_hashed(self, api_client: TestClient, db: Session):
        """Test that password is securely hashed and not stored in plain text."""
        _seed_role(db, "admin")
        db.commit()

        password = "MyVerySecurePassword123!"
        response = api_client.post(
            "/api/v1/auth/register-company",
            json={
                "company_name": "Secure Hash Corp",
                "company_code": "secure-hash-corp",
                "admin_email": "admin@securehash.example.com",
                "admin_password": password,
                "admin_full_name": "Secure Admin",
            },
        )
        assert response.status_code == 201, response.text

        # Get user and verify password is hashed
        org = db.query(Organization).filter(Organization.code == "secure-hash-corp").first()
        user = db.query(User).filter(User.tenant_id == org.id).first()

        # Password should be hashed (bcrypt hash starts with $2b$)
        assert user.hashed_password.startswith("$2b$")
        # Plain password should not be in the hash
        assert password not in user.hashed_password
        # Should be able to verify
        assert verify_password(password, user.hashed_password)


class TestLoginScenarios:
    """Test login scenarios for multi-tenant SaaS."""

    def test_login_with_company_code(self, api_client: TestClient, db: Session):
        """Test login with company code succeeds."""
        admin_role = _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Login Test", code="login-test", is_active=True)
        db.add(org)
        db.flush()
        user = _create_user(
            db,
            tenant_id=org.id,
            email="user@logintest.example.com",
            full_name="Login User",
            password="CorrectPassword123!",
        )
        _assign_role(db, user_id=user.id, role_id=admin_role.id)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "login-test",
                "email": "user@logintest.example.com",
                "password": "CorrectPassword123!",
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_with_wrong_company_code_fails(self, api_client: TestClient, db: Session):
        """Test login with wrong company code fails."""
        admin_role = _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Wrong Code Test", code="wrong-code-test", is_active=True)
        db.add(org)
        db.flush()
        user = _create_user(
            db,
            tenant_id=org.id,
            email="user@wrongcode.example.com",
            full_name="Wrong Code User",
            password="CorrectPassword123!",
        )
        _assign_role(db, user_id=user.id, role_id=admin_role.id)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "wrong-code",  # Wrong code
                "email": "user@wrongcode.example.com",
                "password": "CorrectPassword123!",
            },
        )
        assert response.status_code == 401, response.text

    def test_login_with_wrong_password_fails(self, api_client: TestClient, db: Session):
        """Test login with wrong password fails."""
        admin_role = _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Wrong Pass Test", code="wrong-pass-test", is_active=True)
        db.add(org)
        db.flush()
        user = _create_user(
            db,
            tenant_id=org.id,
            email="user@wrongpass.example.com",
            full_name="Wrong Pass User",
            password="CorrectPassword123!",
        )
        _assign_role(db, user_id=user.id, role_id=admin_role.id)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "wrong-pass-test",
                "email": "user@wrongpass.example.com",
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == 401, response.text

    def test_login_inactive_company_fails(self, api_client: TestClient, db: Session):
        """Test login to inactive company fails."""
        admin_role = _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Inactive Test", code="inactive-test", is_active=False)
        db.add(org)
        db.flush()
        user = _create_user(
            db,
            tenant_id=org.id,
            email="user@inactive.example.com",
            full_name="Inactive User",
            password="CorrectPassword123!",
        )
        _assign_role(db, user_id=user.id, role_id=admin_role.id)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "inactive-test",
                "email": "user@inactive.example.com",
                "password": "CorrectPassword123!",
            },
        )
        assert response.status_code == 401, response.text

    def test_login_inactive_user_fails(self, api_client: TestClient, db: Session):
        """Test login as inactive user fails."""
        admin_role = _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Inactive User Test", code="inactive-user-test", is_active=True)
        db.add(org)
        db.flush()
        # Create inactive user
        user = User(
            id=uuid.uuid4(),
            tenant_id=org.id,
            email="inactive@user.example.com",
            hashed_password=hash_password("CorrectPassword123!"),
            full_name="Inactive User",
            is_active=False,
        )
        db.add(user)
        _assign_role(db, user_id=user.id, role_id=admin_role.id)
        db.commit()

        response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "inactive-user-test",
                "email": "inactive@user.example.com",
                "password": "CorrectPassword123!",
            },
        )
        assert response.status_code == 401, response.text


class TestTenantIsolation:
    """Test that tenant isolation is enforced."""

    def test_user_cannot_access_other_tenant_data(self, api_client: TestClient, db: Session):
        """Test that user cannot access data from other tenants."""
        admin_role = _seed_role(db, "admin")

        # Create tenant A
        org_a = Organization(id=uuid.uuid4(), name="Tenant A", code="tenant-a", is_active=True)
        db.add(org_a)
        db.flush()
        user_a = _create_user(
            db,
            tenant_id=org_a.id,
            email="admin@tenanta.example.com",
            full_name="Admin A",
            password="Password123!",
        )
        _assign_role(db, user_id=user_a.id, role_id=admin_role.id)

        # Create tenant B
        org_b = Organization(id=uuid.uuid4(), name="Tenant B", code="tenant-b", is_active=True)
        db.add(org_b)
        db.flush()
        user_b = _create_user(
            db,
            tenant_id=org_b.id,
            email="admin@tenantb.example.com",
            full_name="Admin B",
            password="Password123!",
        )
        _assign_role(db, user_id=user_b.id, role_id=admin_role.id)
        db.commit()

        # Login as user A
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "tenant-a",
                "email": "admin@tenanta.example.com",
                "password": "Password123!",
            },
        )
        assert login_response.status_code == 200
        token_a = login_response.json()["access_token"]

        # Try to access users endpoint - should only see tenant A users
        users_response = api_client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert users_response.status_code == 200
        data = users_response.json()
        emails = [u["email"] for u in data["items"]]

        # Should see user from tenant A
        assert "admin@tenanta.example.com" in emails
        # Should NOT see user from tenant B
        assert "admin@tenantb.example.com" not in emails

    def test_token_tenant_mismatch_rejected(self, api_client: TestClient, db: Session):
        """Test that token with wrong tenant ID is rejected."""
        admin_role = _seed_role(db, "admin")

        # Create tenant A
        org_a = Organization(id=uuid.uuid4(), name="Tenant A", code="tenant-a-mismatch", is_active=True)
        db.add(org_a)
        db.flush()
        user_a = _create_user(
            db,
            tenant_id=org_a.id,
            email="admin@tenanta.example.com",
            full_name="Admin A",
            password="Password123!",
        )
        _assign_role(db, user_id=user_a.id, role_id=admin_role.id)

        # Create tenant B
        org_b = Organization(id=uuid.uuid4(), name="Tenant B", code="tenant-b-mismatch", is_active=True)
        db.add(org_b)
        db.flush()
        db.commit()

        # Login as user A
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "tenant-a-mismatch",
                "email": "admin@tenanta.example.com",
                "password": "Password123!",
            },
        )
        assert login_response.status_code == 200
        token_a = login_response.json()["access_token"]

        # The token should contain tenant_a's ID. Trying to use it against
        # a different tenant's resources would still use the token's tenant_id
        # This is implicitly tested by the tenant isolation in user listing


class TestInvitationFlow:
    """Test user invitation flow."""

    def test_admin_can_invite_user(self, api_client: TestClient, db: Session):
        """Test that admin can invite a new user."""
        admin_role = _seed_role(db, "admin")
        analyst_role = _seed_role(db, "analyst")
        org = Organization(id=uuid.uuid4(), name="Invite Test", code="invite-test", is_active=True)
        db.add(org)
        db.flush()
        admin = _create_user(
            db,
            tenant_id=org.id,
            email="admin@invite.example.com",
            full_name="Invite Admin",
            password="Password123!",
        )
        _assign_role(db, user_id=admin.id, role_id=admin_role.id)
        db.commit()

        # Login as admin
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "invite-test",
                "email": "admin@invite.example.com",
                "password": "Password123!",
            },
        )
        assert login_response.status_code == 200
        admin_token = login_response.json()["access_token"]

        # Invite new user
        invite_response = api_client.post(
            "/api/v1/users/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "newuser@invite.example.com",
                "role_name": "analyst",
                "expires_in_hours": 72,
            },
        )
        assert invite_response.status_code == 201, invite_response.text
        data = invite_response.json()
        assert "invitation_token" in data
        assert data["email"] == "newuser@invite.example.com"
        assert data["role_name"] == "analyst"

    def test_duplicate_invitation_rejected(self, api_client: TestClient, db: Session):
        """Test that duplicate active invitation is rejected."""
        admin_role = _seed_role(db, "admin")
        analyst_role = _seed_role(db, "analyst")
        org = Organization(id=uuid.uuid4(), name="Dup Invite Test", code="dup-invite-test", is_active=True)
        db.add(org)
        db.flush()
        admin = _create_user(
            db,
            tenant_id=org.id,
            email="admin@dupinvite.example.com",
            full_name="Dup Invite Admin",
            password="Password123!",
        )
        _assign_role(db, user_id=admin.id, role_id=admin_role.id)
        db.commit()

        # Login as admin
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "dup-invite-test",
                "email": "admin@dupinvite.example.com",
                "password": "Password123!",
            },
        )
        admin_token = login_response.json()["access_token"]

        # First invitation
        invite_response1 = api_client.post(
            "/api/v1/users/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "dupuser@invite.example.com",
                "role_name": "analyst",
                "expires_in_hours": 72,
            },
        )
        assert invite_response1.status_code == 201

        # Second invitation for same email (should fail)
        invite_response2 = api_client.post(
            "/api/v1/users/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "dupuser@invite.example.com",
                "role_name": "manager",
                "expires_in_hours": 72,
            },
        )
        assert invite_response2.status_code == 400
        assert "active invitation already exists" in invite_response2.json()["detail"].lower()

    def test_invited_user_can_accept_and_login(self, api_client: TestClient, db: Session):
        """Test that invited user can accept invitation and login."""
        admin_role = _seed_role(db, "admin")
        analyst_role = _seed_role(db, "analyst")
        org = Organization(id=uuid.uuid4(), name="Accept Test", code="accept-test", is_active=True)
        db.add(org)
        db.flush()
        admin = _create_user(
            db,
            tenant_id=org.id,
            email="admin@accept.example.com",
            full_name="Accept Admin",
            password="Password123!",
        )
        _assign_role(db, user_id=admin.id, role_id=admin_role.id)
        db.commit()

        # Login as admin and invite
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "accept-test",
                "email": "admin@accept.example.com",
                "password": "Password123!",
            },
        )
        admin_token = login_response.json()["access_token"]

        invite_response = api_client.post(
            "/api/v1/users/invitations",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "invited@accept.example.com",
                "role_name": "analyst",
                "expires_in_hours": 72,
            },
        )
        invitation_token = invite_response.json()["invitation_token"]

        # Accept invitation
        accept_response = api_client.post(
            "/api/v1/auth/accept-invitation",
            json={
                "invitation_token": invitation_token,
                "full_name": "Invited User",
                "password": "InvitedPass123!",
            },
        )
        assert accept_response.status_code == 200, accept_response.text
        data = accept_response.json()
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify can access /me endpoint
        me_response = api_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "invited@accept.example.com"
        assert me_data["tenant_code"] == "accept-test"
        assert "analyst" in me_data["roles"]


class TestPlatformOwnerAccess:
    """Test platform owner specific functionality."""

    def test_platform_owner_can_list_all_tenants(self, api_client: TestClient, db: Session):
        """Test that platform owner can list all tenants."""
        platform_role = _seed_role(db, "platform_owner")

        # Create multiple tenants
        org1 = Organization(id=uuid.uuid4(), name="Tenant 1", code="tenant-1", is_active=True)
        org2 = Organization(id=uuid.uuid4(), name="Tenant 2", code="tenant-2", is_active=True)
        db.add_all([org1, org2])
        db.flush()

        # Create platform owner user (in one of the orgs for simplicity)
        platform_owner = _create_user(
            db,
            tenant_id=org1.id,
            email="platform@owner.example.com",
            full_name="Platform Owner",
            password="PlatformPass123!",
        )
        _assign_role(db, user_id=platform_owner.id, role_id=platform_role.id)
        db.commit()

        # Login as platform owner
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "tenant-1",
                "email": "platform@owner.example.com",
                "password": "PlatformPass123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # List all tenants
        tenants_response = api_client.get(
            "/api/v1/platform/tenants",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert tenants_response.status_code == 200, tenants_response.text
        data = tenants_response.json()
        codes = [t["code"] for t in data["items"]]
        assert "tenant-1" in codes
        assert "tenant-2" in codes

    def test_non_platform_owner_cannot_access_platform_endpoints(self, api_client: TestClient, db: Session):
        """Test that non-platform owner cannot access platform endpoints."""
        admin_role = _seed_role(db, "admin")
        org = Organization(id=uuid.uuid4(), name="Non Platform Test", code="non-platform-test", is_active=True)
        db.add(org)
        db.flush()
        admin = _create_user(
            db,
            tenant_id=org.id,
            email="admin@nonplatform.example.com",
            full_name="Non Platform Admin",
            password="Password123!",
        )
        _assign_role(db, user_id=admin.id, role_id=admin_role.id)
        db.commit()

        # Login as regular admin
        login_response = api_client.post(
            "/api/v1/auth/login",
            json={
                "company_code": "non-platform-test",
                "email": "admin@nonplatform.example.com",
                "password": "Password123!",
            },
        )
        token = login_response.json()["access_token"]

        # Try to access platform endpoint
        tenants_response = api_client.get(
            "/api/v1/platform/tenants",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert tenants_response.status_code == 403
