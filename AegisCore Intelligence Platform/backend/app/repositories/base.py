"""Base repository with tenant-aware query scoping.

All tenant-scoped repositories should inherit from TenantAwareRepository
to ensure consistent tenant isolation.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Generic, TypeVar

from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.core.tenant import TenantContext

ModelType = TypeVar("ModelType")


class TenantAwareRepository(Generic[ModelType]):
    """Base repository class that enforces tenant scoping on all queries.
    
    Usage:
        class AssetRepository(TenantAwareRepository[Asset]):
            def __init__(self, db: Session):
                super().__init__(db, Asset)
    
    All query methods automatically apply tenant filtering unless
    explicitly called with platform_owner bypass.
    """

    def __init__(
        self,
        db: "Session",
        model_class: type[ModelType],
        tenant_column: str = "tenant_id",
    ):
        self.db = db
        self.model_class = model_class
        self.tenant_column = tenant_column

    def _apply_tenant_scope(
        self,
        stmt,
        tenant_id: uuid.UUID,
    ):
        """Apply tenant filter to a select statement."""
        return stmt.where(getattr(self.model_class, self.tenant_column) == tenant_id)

    def get_by_id(
        self,
        resource_id: uuid.UUID,
        tenant_context: "TenantContext | None" = None,
    ) -> ModelType | None:
        """Get a resource by ID, optionally scoped to tenant.
        
        If tenant_context is provided, enforces tenant isolation.
        Platform owners can access any tenant's resources.
        """
        stmt = select(self.model_class).where(self.model_class.id == resource_id)
        
        if tenant_context is not None and not tenant_context.is_platform_owner:
            stmt = self._apply_tenant_scope(stmt, tenant_context.tenant_id)
        
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        tenant_context: "TenantContext",
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ModelType], int]:
        """List resources scoped to the tenant.
        
        Platform owners see all resources.
        """
        base_stmt = select(self.model_class)
        
        if not tenant_context.is_platform_owner:
            base_stmt = self._apply_tenant_scope(base_stmt, tenant_context.tenant_id)
        
        # Count query
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = self.db.scalar(count_stmt) or 0
        
        # Data query with pagination
        data_stmt = base_stmt.offset(offset).limit(limit)
        rows = self.db.execute(data_stmt).scalars().all()
        
        return list(rows), int(total)

    def create(
        self,
        instance: ModelType,
        tenant_context: "TenantContext | None" = None,
    ) -> ModelType:
        """Create a new resource.
        
        If tenant_context is provided, validates the instance belongs to the tenant.
        """
        if tenant_context is not None and not tenant_context.is_platform_owner:
            instance_tenant_id = getattr(instance, self.tenant_column, None)
            if instance_tenant_id != tenant_context.tenant_id:
                from app.core.tenant import TenantIsolationError
                raise TenantIsolationError(
                    f"Cannot create resource for tenant {instance_tenant_id} "
                    f"as user from tenant {tenant_context.tenant_id}"
                )
        
        self.db.add(instance)
        self.db.flush()
        self.db.refresh(instance)
        return instance

    def delete(
        self,
        instance: ModelType,
        tenant_context: "TenantContext | None" = None,
    ) -> None:
        """Delete a resource, optionally validating tenant ownership."""
        if tenant_context is not None and not tenant_context.is_platform_owner:
            instance_tenant_id = getattr(instance, self.tenant_column, None)
            if instance_tenant_id != tenant_context.tenant_id:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resource not found",
                )
        
        self.db.delete(instance)
        self.db.flush()

    def exists_in_tenant(
        self,
        resource_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Check if a resource exists and belongs to the specified tenant."""
        stmt = (
            select(func.count())
            .select_from(self.model_class)
            .where(self.model_class.id == resource_id)
            .where(getattr(self.model_class, self.tenant_column) == tenant_id)
        )
        return (self.db.scalar(stmt) or 0) > 0


class GlobalRepository(Generic[ModelType]):
    """Repository for global (non-tenant-scoped) entities.
    
    Used for entities like CVE records, roles, etc. that are shared
    across all tenants.
    """

    def __init__(self, db: "Session", model_class: type[ModelType]):
        self.db = db
        self.model_class = model_class

    def get_by_id(self, resource_id: uuid.UUID) -> ModelType | None:
        """Get a global resource by ID."""
        stmt = select(self.model_class).where(self.model_class.id == resource_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[ModelType], int]:
        """List all global resources."""
        base_stmt = select(self.model_class)
        
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = self.db.scalar(count_stmt) or 0
        
        data_stmt = base_stmt.offset(offset).limit(limit)
        rows = self.db.execute(data_stmt).scalars().all()
        
        return list(rows), int(total)
