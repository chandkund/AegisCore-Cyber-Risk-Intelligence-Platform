"""Unit tests for tenant isolation utilities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import FrozenSet

import pytest

from app.core.tenant import (
    TenantContext,
    TenantIsolationError,
    get_tenant_context,
    require_tenant_access,
    scope_query_to_tenant,
)


@dataclass(frozen=True)
class MockPrincipal:
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_code: str
    tenant_name: str
    roles: FrozenSet[str]


class TestTenantContext:
    """Test tenant context creation and validation."""

    def test_get_tenant_context_from_principal(self):
        """Tenant context extracted correctly from authenticated principal."""
        principal = MockPrincipal(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            tenant_code="acme",
            tenant_name="Acme Corp",
            roles=frozenset(["admin"]),
        )
        
        ctx = get_tenant_context(principal)
        
        assert ctx.tenant_id == principal.tenant_id
        assert ctx.tenant_code == "acme"
        assert ctx.tenant_name == "Acme Corp"
        assert ctx.user_id == principal.id
        assert ctx.is_platform_owner is False

    def test_get_tenant_context_for_platform_owner(self):
        """Platform owner role correctly identified in context."""
        principal = MockPrincipal(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            tenant_code="platform",
            tenant_name="Platform",
            roles=frozenset(["platform_owner"]),
        )
        
        ctx = get_tenant_context(principal)
        
        assert ctx.is_platform_owner is True


class TestTenantAccessValidation:
    """Test tenant access validation logic."""

    def test_regular_user_same_tenant_allowed(self):
        """Regular user can access resources in their own tenant."""
        tenant_id = uuid.uuid4()
        ctx = TenantContext(
            tenant_id=tenant_id,
            tenant_code="acme",
            tenant_name="Acme Corp",
            user_id=uuid.uuid4(),
            is_platform_owner=False,
        )
        
        # Should not raise
        ctx.ensure_tenant_scope(tenant_id)

    def test_regular_user_different_tenant_blocked(self):
        """Regular user cannot access resources in different tenant."""
        user_tenant = uuid.uuid4()
        resource_tenant = uuid.uuid4()
        ctx = TenantContext(
            tenant_id=user_tenant,
            tenant_code="acme",
            tenant_name="Acme Corp",
            user_id=uuid.uuid4(),
            is_platform_owner=False,
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            ctx.ensure_tenant_scope(resource_tenant)
        
        assert exc_info.value.status_code == 403
        assert "Cross-tenant access denied" in str(exc_info.value.detail)

    def test_platform_owner_can_access_any_tenant(self):
        """Platform owner can access resources in any tenant."""
        platform_tenant = uuid.uuid4()
        other_tenant = uuid.uuid4()
        ctx = TenantContext(
            tenant_id=platform_tenant,
            tenant_code="platform",
            tenant_name="Platform Owner",
            user_id=uuid.uuid4(),
            is_platform_owner=True,
        )
        
        # Should not raise for any tenant
        ctx.ensure_tenant_scope(other_tenant)
        ctx.ensure_tenant_scope(uuid.uuid4())

    def test_require_tenant_access_allows_same_tenant(self):
        """require_tenant_access allows access to same tenant."""
        tenant_id = uuid.uuid4()
        ctx = TenantContext(
            tenant_id=tenant_id,
            tenant_code="acme",
            tenant_name="Acme Corp",
            user_id=uuid.uuid4(),
            is_platform_owner=False,
        )
        
        # Should not raise
        require_tenant_access(tenant_id, ctx, "asset")

    def test_require_tenant_access_returns_404_for_cross_tenant(self):
        """Cross-tenant access returns 404 (not 403) to avoid leaking existence."""
        user_tenant = uuid.uuid4()
        resource_tenant = uuid.uuid4()
        ctx = TenantContext(
            tenant_id=user_tenant,
            tenant_code="acme",
            tenant_name="Acme Corp",
            user_id=uuid.uuid4(),
            is_platform_owner=False,
        )
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            require_tenant_access(resource_tenant, ctx, "asset")
        
        # Returns 404 to avoid leaking resource existence
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()


class TestTenantIsolationError:
    """Test tenant isolation error handling."""

    def test_tenant_isolation_error_raised(self):
        """TenantIsolationError captures violation details."""
        with pytest.raises(TenantIsolationError) as exc_info:
            raise TenantIsolationError(
                f"Resource belongs to tenant {uuid.uuid4()}, "
                f"but user is from tenant {uuid.uuid4()}"
            )
        
        assert "belongs to tenant" in str(exc_info.value)
