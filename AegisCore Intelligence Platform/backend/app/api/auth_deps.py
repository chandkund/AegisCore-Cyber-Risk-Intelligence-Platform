"""Enhanced authentication and authorization dependencies for AegisCore.

This module provides production-grade RBAC with:
- JWT token verification via HTTPOnly cookies (secure, XSS-resistant)
- Role-based access control
- Company scope enforcement
- User/company status checks
- Cross-tenant access prevention
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Callable
from enum import Enum

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.security import decode_access_token
from app.core.tenant import TenantContext, get_tenant_context
from app.db.deps import get_db
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService

# Cookie-based auth is primary; Bearer is fallback for API clients
security = HTTPBearer(auto_error=False)

# Cookie names
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


class AccessLevel(str, Enum):
    """Access levels for route protection."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    PLATFORM = "platform"


@dataclass(frozen=True)
class Principal:
    """Authenticated user principal with full security context.

    Attributes:
        id: User UUID
        tenant_id: Company UUID (None for platform_owner)
        tenant_code: Company short code
        tenant_name: Company display name
        email: User email
        full_name: User display name
        roles: Set of role names
        is_active: Whether user account is active
        is_platform_owner: Whether user has platform_owner role
        is_company_admin: Whether user has company admin role
    """
    id: uuid.UUID
    tenant_id: uuid.UUID | None  # None for platform_owner
    tenant_code: str | None
    tenant_name: str | None
    email: str
    full_name: str
    roles: frozenset[str]
    is_active: bool = True

    @property
    def is_platform_owner(self) -> bool:
        """Check if user is a platform owner."""
        return rbac.is_platform_owner(self.roles)

    @property
    def is_company_admin(self) -> bool:
        """Check if user is a company admin."""
        return rbac.is_company_admin(self.roles)

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: set[str]) -> bool:
        """Check if user has any of the specified roles."""
        return bool(self.roles & roles)

    def has_minimum_role(self, minimum_role: str) -> bool:
        """Check if user has at least the minimum required role."""
        return rbac.has_minimum_role(self.roles, minimum_role)

    def can_access_tenant(self, tenant_id: uuid.UUID) -> bool:
        """Check if user can access a specific tenant's data.

        Platform owners can access all tenants.
        Other users can only access their own tenant.
        """
        if self.is_platform_owner:
            return True
        return self.tenant_id == tenant_id


def get_token_from_request(request: Request) -> str | None:
    """Extract JWT token from cookie or Authorization header.

    Priority:
    1. HTTPOnly cookie (secure, XSS-resistant)
    2. Authorization Bearer header (fallback for API clients)
    """
    # Try cookie first (secure, HttpOnly)
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if cookie_token:
        return cookie_token

    # Fall back to Bearer header (for API clients, mobile apps)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix

    return None


def get_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Principal:
    """Authenticate and retrieve the current user with full security context.

    This dependency:
    1. Extracts token from HTTPOnly cookie (secure) or Bearer header
    2. Validates the JWT token
    3. Verifies user exists and is active
    4. Verifies company exists and is active (for non-platform-owners)
    5. Builds the Principal with all security context

    Raises:
        HTTPException(401): If authentication fails
    """
    token = get_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate token
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token type
    if payload.get("typ") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token claims
    try:
        user_id = uuid.UUID(str(payload["sub"]))
        token_tenant_id = uuid.UUID(str(payload["tid"])) if payload.get("tid") else None
        token_roles = frozenset(payload.get("roles", []))
    except (KeyError, ValueError, TypeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Load user from database
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        _audit_log_disabled_user_access(db, user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get current roles from database (not token) for security
    current_roles = frozenset(
        ur.role.name for ur in user.roles if ur.role is not None
    )

    # Check for role tampering (token roles don't match database)
    if current_roles != token_roles:
        # Log potential security issue
        _audit_log_role_mismatch(db, user_id, token_roles, current_roles)

    # Handle platform owner (can have NULL tenant_id)
    is_platform_owner = rbac.is_platform_owner(current_roles)

    if is_platform_owner:
        # Platform owner can have NULL tenant_id
        if user.tenant_id is not None and user.tenant_id != token_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token tenant mismatch",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return Principal(
            id=user.id,
            tenant_id=user.tenant_id,  # May be None
            tenant_code=None,  # Platform owner has no specific tenant
            tenant_name=None,
            email=user.email,
            full_name=user.full_name,
            roles=current_roles,
            is_active=user.is_active,
        )

    # Regular user must have tenant_id
    if user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not assigned to a company",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify token tenant matches user tenant
    if token_tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tenant mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load and verify company
    org_repo = OrganizationRepository(db)
    org = org_repo.get_by_id(user.tenant_id)

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Company not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check company is active
    if not org.is_active:
        _audit_log_suspended_company_access(db, user.id, org.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company account is suspended",
        )

    # Check company approval status
    if org.approval_status not in ("approved",):
        if org.approval_status == "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company registration pending approval",
            )
        elif org.approval_status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company registration has been rejected",
            )

    return Principal(
        id=user.id,
        tenant_id=user.tenant_id,
        tenant_code=org.code,
        tenant_name=org.name,
        email=user.email,
        full_name=user.full_name,
        roles=current_roles,
        is_active=user.is_active,
    )


def require_active_user() -> Callable[..., Principal]:
    """Require an active user (additional check beyond get_current_user)."""
    def _check(principal: Annotated[Principal, Depends(get_current_user)]) -> Principal:
        if not principal.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        return principal
    return _check


def require_roles(*allowed_roles: str, allow_platform_owner: bool = True) -> Callable[..., Principal]:
    """Create a dependency that requires specific roles.

    Args:
        allowed_roles: Roles that are permitted
        allow_platform_owner: If True, platform_owner always passes

    Returns:
        Dependency function for FastAPI
    """
    allowed_set = frozenset(allowed_roles)

    def _check(principal: Annotated[Principal, Depends(get_current_user)]) -> Principal:
        # Platform owner bypass (if enabled)
        if allow_platform_owner and principal.is_platform_owner:
            return principal

        # Admin bypass for non-platform endpoints (backward compatibility)
        if rbac.ROLE_PLATFORM_OWNER not in allowed_set:
            if rbac.ROLE_ADMIN in principal.roles and rbac.ROLE_ADMIN in allowed_set:
                return principal

        # Check role membership
        if not (principal.roles & allowed_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}",
            )

        return principal

    return _check


def require_platform_owner() -> Callable[..., Principal]:
    """Require platform_owner role (super admin access)."""
    return require_roles(rbac.ROLE_PLATFORM_OWNER, allow_platform_owner=False)


def require_company_admin() -> Callable[..., Principal]:
    """Require company admin or platform_owner role."""
    return require_roles(rbac.ROLE_ADMIN, rbac.ROLE_PLATFORM_OWNER)


def require_analyst() -> Callable[..., Principal]:
    """Require analyst or higher role."""
    return require_roles(
        rbac.ROLE_ANALYST,
        rbac.ROLE_ADMIN,
        rbac.ROLE_PLATFORM_OWNER
    )


def require_manager() -> Callable[..., Principal]:
    """Require manager or higher role."""
    return require_roles(
        rbac.ROLE_MANAGER,
        rbac.ROLE_ANALYST,
        rbac.ROLE_ADMIN,
        rbac.ROLE_PLATFORM_OWNER
    )


def require_viewer() -> Callable[..., Principal]:
    """Require any read role (lowest privilege level)."""
    return require_roles(
        rbac.ROLE_VIEWER,
        rbac.ROLE_MANAGER,
        rbac.ROLE_ANALYST,
        rbac.ROLE_ADMIN,
        rbac.ROLE_PLATFORM_OWNER
    )


def require_same_company(
    principal: Principal,
    target_tenant_id: uuid.UUID,
    action: str = "access"
) -> None:
    """Enforce that a user can only access their own company's data.

    Args:
        principal: The authenticated user
        target_tenant_id: The company ID being accessed
        action: Description of the action for error messages

    Raises:
        HTTPException(403): If user tries to access another company's data
    """
    # Platform owners can access any company
    if principal.is_platform_owner:
        return

    # Regular users can only access their own company
    if principal.tenant_id != target_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot {action} data from another company",
        )


def require_same_company_or_platform(
    principal: Principal,
    target_tenant_id: uuid.UUID | None = None,
    target_user_id: uuid.UUID | None = None,
    db: Session | None = None,
) -> None:
    """Enforce company scope with platform owner exception.

    This is a more flexible version that handles both direct tenant_id checks
    and user-based checks (looking up the user's company).
    """
    # Platform owners bypass all checks
    if principal.is_platform_owner:
        return

    # Determine target tenant
    if target_tenant_id:
        effective_tenant = target_tenant_id
    elif target_user_id and db:
        user_repo = UserRepository(db)
        target_user = user_repo.get_by_id(target_user_id)
        if target_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user not found",
            )
        effective_tenant = target_user.tenant_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify target_tenant_id or target_user_id",
        )

    # Check access
    if principal.tenant_id != effective_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access resources from another company",
        )


def enforce_company_scope(
    principal: Principal,
    tenant_context: TenantContext,
) -> None:
    """Verify that the request tenant context matches the user's company.

    This prevents users from manipulating tenant context in requests.
    """
    if principal.is_platform_owner:
        return

    if principal.tenant_id != tenant_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context mismatch with authenticated user",
        )


# =============================================================================
# FastAPI Dependency Aliases (for route decorators)
# =============================================================================

# Platform owner only
PlatformOwnerDep = Annotated[Principal, Depends(require_platform_owner())]

# Company admin or platform owner
CompanyAdminDep = Annotated[Principal, Depends(require_company_admin())]

# Admin alias (same as CompanyAdminDep for backward compatibility)
AdminDep = CompanyAdminDep

# Analyst or higher
AnalystDep = Annotated[Principal, Depends(require_analyst())]

# Manager or higher
ManagerDep = Annotated[Principal, Depends(require_manager())]

# Viewer or higher (any authenticated user with read access)
ViewerDep = Annotated[Principal, Depends(require_viewer())]

# Writer alias (analyst or higher, for backward compatibility)
WriterDep = AnalystDep

# Reader alias (any read role, for backward compatibility)
ReaderDep = ViewerDep

# Current user (no role checks, just authentication)
CurrentUserDep = Annotated[Principal, Depends(get_current_user)]

# Active user (authentication + active check)
ActiveUserDep = Annotated[Principal, Depends(require_active_user())]


# =============================================================================
# Audit Logging Helpers
# =============================================================================

def _audit_log_disabled_user_access(db: Session, user_id: uuid.UUID) -> None:
    """Log attempt by disabled user to access system."""
    try:
        audit = AuditService(db)
        audit.record(
            actor_user_id=user_id,
            action="DISABLED_USER_ACCESS_ATTEMPT",
            resource_type="authentication",
            payload={"reason": "User account is disabled"},
        )
        db.commit()
    except Exception:
        pass  # Don't fail auth due to audit logging issues


def _audit_log_suspended_company_access(
    db: Session, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> None:
    """Log attempt to access suspended company."""
    try:
        audit = AuditService(db)
        audit.record(
            actor_user_id=user_id,
            action="SUSPENDED_COMPANY_ACCESS_ATTEMPT",
            resource_type="authentication",
            tenant_id=tenant_id,
            payload={"reason": "Company account is suspended"},
        )
        db.commit()
    except Exception:
        pass


def _audit_log_role_mismatch(
    db: Session,
    user_id: uuid.UUID,
    token_roles: frozenset[str],
    db_roles: frozenset[str],
) -> None:
    """Log potential token tampering (roles don't match database)."""
    try:
        audit = AuditService(db)
        audit.record(
            actor_user_id=user_id,
            action="TOKEN_ROLE_MISMATCH",
            resource_type="security",
            payload={
                "token_roles": list(token_roles),
                "database_roles": list(db_roles),
                "severity": "warning",
            },
        )
        db.commit()
    except Exception:
        pass
