from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.email_verification import EmailVerification
from app.core.security import hash_password
from app.models.oltp import Organization, Role, User, UserRole


def _seed_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).one_or_none()
    if role is not None:
        return role
    role = Role(id=uuid.uuid4(), name=name, description=f"{name} role")
    db.add(role)
    db.flush()
    return role


def _create_user(db: Session, *, tenant_id: uuid.UUID, email: str, full_name: str, password: str) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email.lower(),
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _assign_role(db: Session, *, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
    db.add(UserRole(user_id=user_id, role_id=role_id))
    db.flush()


def test_company_registration_and_me(api_client: TestClient, db: Session):
    _seed_role(db, "admin")
    db.commit()

    response = api_client.post(
        "/api/v1/auth/register-company",
        json={
            "company_name": "Acme Security",
            "company_code": "acme-sec",
            "admin_email": "admin@acme.example.com",
            "admin_password": "AegisCore!VerySecure123",
            "admin_full_name": "Acme Admin",
        },
    )
    assert response.status_code == 201, response.text
    registration = response.json()
    user_id = registration["user_id"]
    verification = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == uuid.UUID(user_id))
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    assert verification is not None
    verified = api_client.post(
        "/api/v1/auth/verify-email",
        json={"user_id": user_id, "code": verification.code},
    )
    assert verified.status_code == 200, verified.text
    token = verified.json()["access_token"]

    me = api_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    payload = me.json()
    assert payload["tenant_code"] == "acme-sec"
    assert payload["tenant_name"] == "Acme Security"
    assert "admin" in payload["roles"]
    assert payload["is_platform_owner"] is False


def test_login_requires_tenant_context_when_email_exists_in_multiple_tenants(
    api_client: TestClient, db: Session
):
    admin_role = _seed_role(db, "admin")
    org_a = Organization(id=uuid.uuid4(), name="Tenant A", code="ten-a", is_active=True)
    org_b = Organization(id=uuid.uuid4(), name="Tenant B", code="ten-b", is_active=True)
    db.add_all([org_a, org_b])
    db.flush()
    user_a = _create_user(
        db,
        tenant_id=org_a.id,
        email="shared@user.example.com",
        full_name="Shared A",
        password="AegisCore!Password123",
    )
    user_b = _create_user(
        db,
        tenant_id=org_b.id,
        email="shared@user.example.com",
        full_name="Shared B",
        password="AegisCore!Password123",
    )
    _assign_role(db, user_id=user_a.id, role_id=admin_role.id)
    _assign_role(db, user_id=user_b.id, role_id=admin_role.id)
    db.commit()

    missing_tenant = api_client.post(
        "/api/v1/auth/login",
        json={"email": "shared@user.example.com", "password": "AegisCore!Password123"},
    )
    assert missing_tenant.status_code == 401

    valid = api_client.post(
        "/api/v1/auth/login",
        json={
            "company_code": "ten-a",
            "email": "shared@user.example.com",
            "password": "AegisCore!Password123",
        },
    )
    assert valid.status_code == 200, valid.text


def test_admin_invitation_acceptance_and_tenant_isolation(api_client: TestClient, db: Session):
    admin_role = _seed_role(db, "admin")
    _seed_role(db, "analyst")
    org = Organization(id=uuid.uuid4(), name="Invite Org", code="invite-org", is_active=True)
    db.add(org)
    db.flush()
    admin = _create_user(
        db,
        tenant_id=org.id,
        email="admin@invite.example.com",
        full_name="Invite Admin",
        password="AegisCore!Password123",
    )
    _assign_role(db, user_id=admin.id, role_id=admin_role.id)
    db.commit()

    login = api_client.post(
        "/api/v1/auth/login",
        json={
            "company_code": "invite-org",
            "email": "admin@invite.example.com",
            "password": "AegisCore!Password123",
        },
    )
    assert login.status_code == 200, login.text
    admin_token = login.json()["access_token"]

    invite = api_client.post(
        "/api/v1/users/invitations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "analyst@invite.example.com", "role_name": "analyst", "expires_in_hours": 24},
    )
    assert invite.status_code == 201, invite.text
    invitation_token = invite.json()["invitation_token"]

    accepted = api_client.post(
        "/api/v1/auth/accept-invitation",
        json={
            "invitation_token": invitation_token,
            "full_name": "Invited Analyst",
            "password": "AegisCore!Password123",
        },
    )
    assert accepted.status_code == 200, accepted.text
    invited_access = accepted.json()["access_token"]

    invited_me = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {invited_access}"},
    )
    assert invited_me.status_code == 200
    assert invited_me.json()["tenant_code"] == "invite-org"
    assert "analyst" in invited_me.json()["roles"]

    users = api_client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users.status_code in [200, 403]
    if users.status_code == 200:
        emails = {item["email"] for item in users.json()["items"]}
        assert "admin@invite.example.com" in emails
        assert "analyst@invite.example.com" in emails
