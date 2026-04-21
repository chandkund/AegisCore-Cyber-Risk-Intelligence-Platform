"""Authentication and authorization dependencies (backward compatibility shim).

This module re-exports from auth_deps.py for backward compatibility.
New code should import directly from auth_deps.py.
"""

from __future__ import annotations

# Re-export all authentication dependencies from the new auth_deps module
from app.api.auth_deps import (
    # Principal class
    Principal,
    AccessLevel,
    # Core dependencies
    get_current_user,
    require_active_user,
    require_roles,
    require_platform_owner,
    require_company_admin,
    require_analyst,
    require_manager,
    require_viewer,
    # Company scope enforcement
    require_same_company,
    require_same_company_or_platform,
    enforce_company_scope,
    # Typed dependencies for route decorators
    PlatformOwnerDep,
    CompanyAdminDep,
    AdminDep,  # Alias for backward compatibility
    AnalystDep,
    WriterDep,  # Alias for backward compatibility
    ManagerDep,
    ViewerDep,
    ReaderDep,  # Alias for backward compatibility
    CurrentUserDep,
    ActiveUserDep,
    # Security utilities
    security,
)
from fastapi.security import HTTPAuthorizationCredentials

# Keep TenantContextDep here as it's related to auth context
from typing import Annotated
from fastapi import Depends
from app.core.tenant import TenantContext, get_tenant_context
from app.api.auth_deps import get_current_user as _get_current_user


def _get_tenant_context_dep(
    principal: Annotated[Principal, Depends(_get_current_user)]
) -> TenantContext:
    """Derive tenant context from authenticated user.

    Never trust client-provided tenant identifiers.
    """
    return get_tenant_context(principal)


TenantContextDep = Annotated[TenantContext, Depends(_get_tenant_context_dep)]


def get_principal_from_token(token: str, db) -> Principal:
    """Backward-compatible helper to resolve Principal from raw JWT."""
    cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return get_current_user(cred, db)
