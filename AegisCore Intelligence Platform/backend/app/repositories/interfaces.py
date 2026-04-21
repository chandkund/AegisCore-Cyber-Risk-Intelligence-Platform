"""Repository interfaces for dependency injection.

Defines abstract interfaces for all repositories following the
Repository Pattern. This enables:
- Dependency injection
- Easy testing with mocks
- Swapping implementations (e.g., cache layer)
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

from app.models.user import User
from app.models.organization import Organization
from app.models.security import AuditLog, SecurityEvent
from app.models.job import Job
from app.models.policy import PolicyRule

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Base repository interface."""
    
    @abstractmethod
    def get_by_id(self, id: uuid.UUID) -> Optional[T]:
        """Get entity by ID."""
        raise NotImplementedError
    
    @abstractmethod
    def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List all entities with pagination."""
        raise NotImplementedError
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity."""
        raise NotImplementedError
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, id: uuid.UUID) -> bool:
        """Delete an entity. Returns True if deleted."""
        raise NotImplementedError


class IUserRepository(IRepository[User]):
    """User repository interface."""
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        raise NotImplementedError
    
    @abstractmethod
    def get_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[User]:
        """Get all users in a tenant."""
        raise NotImplementedError
    
    @abstractmethod
    def get_active_users(self, tenant_id: uuid.UUID) -> list[User]:
        """Get only active users in a tenant."""
        raise NotImplementedError
    
    @abstractmethod
    def search_by_name(self, tenant_id: uuid.UUID, query: str) -> list[User]:
        """Search users by name."""
        raise NotImplementedError
    
    @abstractmethod
    def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        """Count users in a tenant."""
        raise NotImplementedError
    
    @abstractmethod
    def update_last_login(self, user_id: uuid.UUID) -> None:
        """Update user's last login timestamp."""
        raise NotImplementedError
    
    @abstractmethod
    def add_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Add role to user."""
        raise NotImplementedError
    
    @abstractmethod
    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Remove role from user."""
        raise NotImplementedError


class IOrganizationRepository(IRepository[Organization]):
    """Organization repository interface."""
    
    @abstractmethod
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        raise NotImplementedError
    
    @abstractmethod
    def get_by_user(self, user_id: uuid.UUID) -> list[Organization]:
        """Get organizations where user is a member."""
        raise NotImplementedError
    
    @abstractmethod
    def update_settings(self, org_id: uuid.UUID, settings: dict) -> Organization:
        """Update organization settings."""
        raise NotImplementedError


class IAuditLogRepository(IRepository[AuditLog]):
    """Audit log repository interface."""
    
    @abstractmethod
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Get audit logs for a tenant."""
        raise NotImplementedError
    
    @abstractmethod
    def get_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs for a user."""
        raise NotImplementedError
    
    @abstractmethod
    def get_by_action(
        self,
        action: str,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Get audit logs by action type."""
        raise NotImplementedError
    
    @abstractmethod
    def get_recent(
        self,
        tenant_id: uuid.UUID,
        minutes: int = 60,
    ) -> list[AuditLog]:
        """Get recent audit logs."""
        raise NotImplementedError


class IJobRepository(IRepository[Job]):
    """Job repository interface."""
    
    @abstractmethod
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """Get jobs for a tenant, optionally filtered by status."""
        raise NotImplementedError
    
    @abstractmethod
    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        """Get pending jobs for processing."""
        raise NotImplementedError
    
    @abstractmethod
    def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        progress: Optional[int] = None,
    ) -> Job:
        """Update job status and progress."""
        raise NotImplementedError
    
    @abstractmethod
    def count_by_status(self, tenant_id: uuid.UUID) -> dict[str, int]:
        """Count jobs by status."""
        raise NotImplementedError


class IPolicyRepository(IRepository[PolicyRule]):
    """Policy repository interface."""
    
    @abstractmethod
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        enabled_only: bool = True,
    ) -> list[PolicyRule]:
        """Get policies for a tenant."""
        raise NotImplementedError
    
    @abstractmethod
    def get_enabled(self, tenant_id: uuid.UUID) -> list[PolicyRule]:
        """Get only enabled policies."""
        raise NotImplementedError
