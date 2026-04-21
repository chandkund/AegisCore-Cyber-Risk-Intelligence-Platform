"""Dependency Injection Container.

Centralizes all dependency registration and resolution.
Enables clean separation and easy testing.

Usage:
    from app.core.di_container import container
    
    # In production
    user_repo = container.user_repository()
    
    # In tests
    container.register(IUserRepository, MockUserRepository)
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.repositories.interfaces import (
    IUserRepository,
    IOrganizationRepository,
    IAuditLogRepository,
    IJobRepository,
    IPolicyRepository,
)
from app.repositories.sqlalchemy_repositories import (
    UserRepository,
    OrganizationRepository,
    AuditLogRepository,
    JobRepository,
    PolicyRepository,
)

T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container.
    
    Supports:
    - Interface-to-implementation mapping
    - Factory registration
    - Singleton instances
    - Context-aware resolution (with DB session)
    """
    
    def __init__(self):
        self._registrations: dict[Type, Any] = {}
        self._factories: dict[Type, Callable[..., Any]] = {}
        self._singletons: dict[Type, Any] = {}
    
    def register(
        self,
        interface: Type[T],
        implementation: Type[T] | Callable[..., T],
        singleton: bool = False,
    ) -> None:
        """Register an implementation for an interface.
        
        Args:
            interface: The interface/abstract class
            implementation: Concrete class or factory function
            singleton: Whether to create only one instance
        """
        if singleton and isinstance(implementation, type):
            # Create singleton instance immediately
            self._singletons[interface] = implementation()
        else:
            self._registrations[interface] = implementation
    
    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[..., T],
    ) -> None:
        """Register a factory function for creating instances.
        
        Args:
            interface: The interface to implement
            factory: Function that creates instances
        """
        self._factories[interface] = factory
    
    def resolve(self, interface: Type[T], **kwargs) -> T:
        """Resolve an interface to an instance.
        
        Args:
            interface: The interface to resolve
            **kwargs: Constructor arguments
            
        Returns:
            Instance implementing the interface
            
        Raises:
            KeyError: If interface not registered
        """
        # Check singletons
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check factories
        if interface in self._factories:
            return self._factories[interface](**kwargs)
        
        # Check registrations
        if interface in self._registrations:
            impl = self._registrations[interface]
            if isinstance(impl, type):
                return impl(**kwargs)
            return impl
        
        raise KeyError(f"No registration found for {interface.__name__}")
    
    def get_db(self) -> Session:
        """Get database session."""
        return SessionLocal()


# Global container instance
container = DIContainer()


def register_default_implementations() -> None:
    """Register default production implementations."""
    # Repositories with DB session dependency
    container.register_factory(
        IUserRepository,
        lambda **kwargs: UserRepository(kwargs.get("db") or container.get_db()),
    )
    container.register_factory(
        IOrganizationRepository,
        lambda **kwargs: OrganizationRepository(kwargs.get("db") or container.get_db()),
    )
    container.register_factory(
        IAuditLogRepository,
        lambda **kwargs: AuditLogRepository(kwargs.get("db") or container.get_db()),
    )
    container.register_factory(
        IJobRepository,
        lambda **kwargs: JobRepository(kwargs.get("db") or container.get_db()),
    )
    container.register_factory(
        IPolicyRepository,
        lambda **kwargs: PolicyRepository(kwargs.get("db") or container.get_db()),
    )


# Register defaults on module load
register_default_implementations()


# Convenience getters for FastAPI dependencies
def get_user_repository(db: Session) -> IUserRepository:
    """Get user repository with DB session."""
    return container.resolve(IUserRepository, db=db)


def get_organization_repository(db: Session) -> IOrganizationRepository:
    """Get organization repository with DB session."""
    return container.resolve(IOrganizationRepository, db=db)


def get_audit_log_repository(db: Session) -> IAuditLogRepository:
    """Get audit log repository with DB session."""
    return container.resolve(IAuditLogRepository, db=db)


def get_job_repository(db: Session) -> IJobRepository:
    """Get job repository with DB session."""
    return container.resolve(IJobRepository, db=db)


def get_policy_repository(db: Session) -> IPolicyRepository:
    """Get policy repository with DB session."""
    return container.resolve(IPolicyRepository, db=db)
