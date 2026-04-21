"""Role names align with `database/seeds/roles.csv`.

Role hierarchy (highest to lowest privilege):
1. platform_owner - Super admin, cross-tenant access
2. admin / company_admin - Company administrator
3. analyst - Can update vulnerabilities, create tickets
4. manager - Read-focused with limited write
5. viewer - Read-only access
"""

# Super admin / Platform owner
ROLE_PLATFORM_OWNER = "platform_owner"

# Company-level roles
ROLE_ADMIN = "admin"  # Company administrator (same as company_admin)
ROLE_COMPANY_ADMIN = "admin"  # Alias for clarity
ROLE_ANALYST = "analyst"
ROLE_MANAGER = "manager"
ROLE_VIEWER = "viewer"

# Role collections for convenience
ALL_ROLES = frozenset({
    ROLE_PLATFORM_OWNER,
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_MANAGER,
    ROLE_VIEWER,
})

# Role hierarchy for permission checking (higher index = more permissions)
ROLE_HIERARCHY = [
    ROLE_VIEWER,          # 0 - Read only
    ROLE_MANAGER,         # 1 - Read + limited write
    ROLE_ANALYST,         # 2 - Read + operational write
    ROLE_ADMIN,           # 3 - Full company access
    ROLE_PLATFORM_OWNER,  # 4 - Cross-company access
]


def has_minimum_role(user_roles: frozenset[str], minimum_role: str) -> bool:
    """Check if user has at least the minimum required role.

    Args:
        user_roles: Set of roles the user has
        minimum_role: Minimum role required

    Returns:
        True if user has minimum_role or higher in hierarchy
    """
    if ROLE_PLATFORM_OWNER in user_roles:
        return True  # Platform owner has all permissions

    if minimum_role not in ROLE_HIERARCHY:
        return minimum_role in user_roles  # Unknown role, check exact match

    min_index = ROLE_HIERARCHY.index(minimum_role)
    user_indices = [
        ROLE_HIERARCHY.index(r) for r in user_roles if r in ROLE_HIERARCHY
    ]

    if not user_indices:
        return False

    return max(user_indices) >= min_index


def is_platform_owner(user_roles: frozenset[str]) -> bool:
    """Check if user has platform_owner role."""
    return ROLE_PLATFORM_OWNER in user_roles


def is_company_admin(user_roles: frozenset[str]) -> bool:
    """Check if user has admin role for their company."""
    return ROLE_ADMIN in user_roles or ROLE_PLATFORM_OWNER in user_roles
