"""Multi-tenant data isolation utilities.

This module provides enforcement mechanisms for strict tenant isolation:
- Tenant context extraction from authenticated principal
- Query scoping utilities for repositories
- Validation decorators for service methods
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar

from fastapi import Depends, HTTPException, status

if TYPE_CHECKING:
    from sqlalchemy.orm import Query, Session

    from app.api.deps import Principal

T = TypeVar("T")


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context extracted from authenticated user."""
    tenant_id: uuid.UUID
    tenant_code: str | None = None
    tenant_name: str | None = None
    user_id: uuid.UUID | None = None
    is_platform_owner: bool = False

    def ensure_tenant_scope(self, resource_tenant_id: uuid.UUID | None) -> None:
        """Validate that a resource belongs to the current tenant.
        
        Platform owners can access all tenants.
        """
        if self.is_platform_owner:
            return
        if resource_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Resource tenant context missing",
            )
        if resource_tenant_id != self.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-tenant access denied",
            )


def get_tenant_context(principal: "Principal") -> TenantContext:
    """Extract tenant context from authenticated principal.
    
    This is the single source of truth for tenant context in the application.
    Never trust client-provided tenant identifiers.
    """
    return TenantContext(
        tenant_id=principal.tenant_id,
        tenant_code=principal.tenant_code,
        tenant_name=principal.tenant_name,
        user_id=principal.id,
        is_platform_owner="platform_owner" in principal.roles,
    )


def scope_query_to_tenant(
    query: "Query[T]",
    tenant_id: uuid.UUID,
    tenant_column: str = "tenant_id",
) -> "Query[T]":
    """Apply tenant filter to a SQLAlchemy query.
    
    Usage:
        query = scope_query_to_tenant(
            session.query(Asset),
            tenant_context.tenant_id
        )
    """
    return query.filter(getattr(query.column_descriptions[0]["entity"], tenant_column) == tenant_id)


def require_tenant_access(
    resource_tenant_id: uuid.UUID | None,
    tenant_context: TenantContext,
    resource_type: str = "resource",
) -> None:
    """Validate tenant access for a resource.
    
    Raises HTTPException if access is denied.
    """
    if tenant_context.is_platform_owner:
        return
    
    if resource_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} not found",
        )
    
    if resource_tenant_id != tenant_context.tenant_id:
        # Log potential security violation
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_type} not found",
        )


def tenant_scoped(service_method: Callable) -> Callable:
    """Decorator to enforce tenant scoping on service methods.
    
    Expects the first argument after 'self' to be a TenantContext.
    
    Usage:
        @tenant_scoped
        def get_asset(self, ctx: TenantContext, asset_id: UUID) -> Asset:
            ...
    """
    @wraps(service_method)
    def wrapper(self, ctx: TenantContext, *args, **kwargs):
        # Validate tenant context is present
        if not isinstance(ctx, TenantContext):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Tenant context required for tenant-scoped operations",
            )
        return service_method(self, ctx, *args, **kwargs)
    return wrapper


class TenantIsolationError(Exception):
    """Raised when a tenant isolation violation is detected."""
    pass


def validate_tenant_ownership(
    session: "Session",
    model_class: type,
    resource_id: uuid.UUID,
    tenant_id: uuid.UUID,
    tenant_context: TenantContext,
) -> bool:
    """Validate that a resource belongs to the specified tenant.
    
    Returns True if valid, raises TenantIsolationError if invalid.
    """
    if tenant_context.is_platform_owner:
        return True
    
    resource = session.get(model_class, resource_id)
    if resource is None:
        raise TenantIsolationError(f"Resource {resource_id} not found")
    
    resource_tenant_id = getattr(resource, "tenant_id", None)
    if resource_tenant_id != tenant_id:
        raise TenantIsolationError(
            f"Resource {resource_id} belongs to tenant {resource_tenant_id}, "
            f"but user is from tenant {tenant_id}"
        )
    
    return True
