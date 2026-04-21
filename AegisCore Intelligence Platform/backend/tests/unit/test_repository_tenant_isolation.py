"""Unit tests for repository tenant isolation.

These tests verify that repository methods correctly enforce tenant scoping
and prevent cross-tenant data access.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.oltp import Organization, Role, User, UserRole
from app.repositories.user_repository import UserRepository


def _create_org(db: Session, name: str, code: str) -> Organization:
    """Helper to create a test organization."""
    org = Organization(
        name=name,
        code=code,
        is_active=True,
        approval_status="approved",
    )
    db.add(org)
    db.flush()
    return org


def _create_user(db: Session, tenant_id: uuid.UUID, email: str, full_name: str) -> User:
    """Helper to create a test user."""
    user = User(
        tenant_id=tenant_id,
        email=email,
        full_name=full_name,
        hashed_password=hash_password("TestPass123!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


class TestUserRepositoryTenantIsolation:
    """Test that UserRepository methods enforce tenant scoping."""

    def test_get_by_id_with_tenant_id_returns_only_same_tenant_user(
        self, db: Session
    ):
        """get_by_id with tenant_id should only return user from that tenant."""
        # Create two tenants
        tenant_a = _create_org(db, "Tenant A", "tenant-a")
        tenant_b = _create_org(db, "Tenant B", "tenant-b")

        # Create users with same email in different tenants
        user_a = _create_user(db, tenant_a.id, "user@example.com", "User A")
        user_b = _create_user(db, tenant_b.id, "user@example.com", "User B")
        db.commit()

        repo = UserRepository(db)

        # With tenant_id, should only return user from that tenant
        result_a = repo.get_by_id(user_a.id, tenant_id=tenant_a.id)
        assert result_a is not None
        assert result_a.id == user_a.id
        assert result_a.tenant_id == tenant_a.id

        # Query for tenant A user with tenant B ID should return None
        result_cross = repo.get_by_id(user_a.id, tenant_id=tenant_b.id)
        assert result_cross is None

        # Query for tenant B user with tenant A ID should return None
        result_cross_b = repo.get_by_id(user_b.id, tenant_id=tenant_a.id)
        assert result_cross_b is None

    def test_get_by_id_without_tenant_id_returns_any_user(
        self, db: Session
    ):
        """get_by_id without tenant_id can return user from any tenant (for platform owner use)."""
        tenant_a = _create_org(db, "Tenant A", "tenant-a")
        user_a = _create_user(db, tenant_a.id, "user@example.com", "User A")
        db.commit()

        repo = UserRepository(db)

        # Without tenant_id, should return user from any tenant
        result = repo.get_by_id(user_a.id)
        assert result is not None
        assert result.id == user_a.id

    def test_list_by_email_with_tenant_id_returns_only_same_tenant_users(
        self, db: Session
    ):
        """list_by_email with tenant_id should only return users from that tenant."""
        tenant_a = _create_org(db, "Tenant A", "tenant-a")
        tenant_b = _create_org(db, "Tenant B", "tenant-b")

        # Create users with same email in different tenants
        user_a = _create_user(db, tenant_a.id, "shared@example.com", "User A")
        user_b = _create_user(db, tenant_b.id, "shared@example.com", "User B")
        db.commit()

        repo = UserRepository(db)

        # With tenant_id, should only return user from that tenant
        results_a = repo.list_by_email("shared@example.com", tenant_id=tenant_a.id)
        assert len(results_a) == 1
        assert results_a[0].id == user_a.id

        results_b = repo.list_by_email("shared@example.com", tenant_id=tenant_b.id)
        assert len(results_b) == 1
        assert results_b[0].id == user_b.id

    def test_list_by_email_without_tenant_id_returns_all_matching_users(
        self, db: Session
    ):
        """list_by_email without tenant_id returns users from all tenants."""
        tenant_a = _create_org(db, "Tenant A", "tenant-a")
        tenant_b = _create_org(db, "Tenant B", "tenant-b")

        # Create users with same email in different tenants
        user_a = _create_user(db, tenant_a.id, "shared@example.com", "User A")
        user_b = _create_user(db, tenant_b.id, "shared@example.com", "User B")
        db.commit()

        repo = UserRepository(db)

        # Without tenant_id, should return all matching users (for platform owner)
        results = repo.list_by_email("shared@example.com")
        assert len(results) == 2
        ids = {u.id for u in results}
        assert user_a.id in ids
        assert user_b.id in ids

    def test_list_users_by_tenant_returns_only_same_tenant_users(
        self, db: Session
    ):
        """list_users_by_tenant should only return users from the specified tenant."""
        tenant_a = _create_org(db, "Tenant A", "tenant-a")
        tenant_b = _create_org(db, "Tenant B", "tenant-b")

        # Create users in both tenants
        _create_user(db, tenant_a.id, "user1@a.com", "User A1")
        _create_user(db, tenant_a.id, "user2@a.com", "User A2")
        _create_user(db, tenant_b.id, "user1@b.com", "User B1")
        db.commit()

        repo = UserRepository(db)

        # Should only return users from tenant A
        users_a, total_a = repo.list_users_by_tenant(tenant_id=tenant_a.id, limit=10, offset=0)
        assert total_a == 2
        assert len(users_a) == 2
        for u in users_a:
            assert u.tenant_id == tenant_a.id

        # Should only return users from tenant B
        users_b, total_b = repo.list_users_by_tenant(tenant_id=tenant_b.id, limit=10, offset=0)
        assert total_b == 1
        assert len(users_b) == 1
        assert users_b[0].tenant_id == tenant_b.id

    def test_get_by_email_with_tenant_id_returns_only_same_tenant_user(
        self, db: Session
    ):
        """get_by_email with tenant_id should only return user from that tenant."""
        tenant_a = _create_org(db, "Tenant A", "tenant-a")
        tenant_b = _create_org(db, "Tenant B", "tenant-b")

        # Create users with same email in different tenants
        user_a = _create_user(db, tenant_a.id, "shared@example.com", "User A")
        user_b = _create_user(db, tenant_b.id, "shared@example.com", "User B")
        db.commit()

        repo = UserRepository(db)

        # With tenant_id, should only return user from that tenant
        result_a = repo.get_by_email("shared@example.com", tenant_id=tenant_a.id)
        assert result_a is not None
        assert result_a.id == user_a.id

        result_b = repo.get_by_email("shared@example.com", tenant_id=tenant_b.id)
        assert result_b is not None
        assert result_b.id == user_b.id

        # Without tenant_id, when multiple users have same email, should raise or return None
        # This is expected behavior - tenant_id should always be provided for tenant-scoped lookups
        with pytest.raises(Exception):  # MultipleResultsFound
            repo.get_by_email("shared@example.com")
