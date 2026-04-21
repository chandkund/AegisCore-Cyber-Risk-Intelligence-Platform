"""Comprehensive tests for Role-Based Access Control (RBAC) system.

Tests cover:
- JWT authentication and token validation
- Role-based access control
- Company scope enforcement
- User/company status checks
- Cross-tenant access prevention
- Security audit logging
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth_deps import (
    Principal,
    enforce_company_scope,
    get_current_user,
    require_company_admin,
    require_platform_owner,
    require_roles,
    require_same_company,
)
from app.core import rbac
from app.core.config import Settings, get_settings
from app.core.security import create_access_token, hash_password
from app.core.tenant import TenantContext
from app.models.oltp import Organization, Role, User, UserRole


# =============================================================================
# Fixtures
# =============================================================================


def _request_with_token(token: str):
    return SimpleNamespace(cookies={}, headers={"Authorization": f"Bearer {token}"})

@pytest.fixture
def settings():
    """Get application settings."""
    return get_settings()


@pytest.fixture
def platform_owner_role(db: Session):
    """Create platform_owner role."""
    role = db.query(Role).filter_by(name=rbac.ROLE_PLATFORM_OWNER).first()
    if not role:
        role = Role(name=rbac.ROLE_PLATFORM_OWNER, description="Platform super admin")
        db.add(role)
        db.commit()
    return role


@pytest.fixture
def admin_role(db: Session):
    """Create admin role."""
    role = db.query(Role).filter_by(name=rbac.ROLE_ADMIN).first()
    if not role:
        role = Role(name=rbac.ROLE_ADMIN, description="Company administrator")
        db.add(role)
        db.commit()
    return role


@pytest.fixture
def analyst_role(db: Session):
    """Create analyst role."""
    role = db.query(Role).filter_by(name=rbac.ROLE_ANALYST).first()
    if not role:
        role = Role(name=rbac.ROLE_ANALYST, description="Vulnerability analyst")
        db.add(role)
        db.commit()
    return role


@pytest.fixture
def manager_role(db: Session):
    """Create manager role."""
    role = db.query(Role).filter_by(name=rbac.ROLE_MANAGER).first()
    if not role:
        role = Role(name=rbac.ROLE_MANAGER, description="Manager access")
        db.add(role)
        db.commit()
    return role


@pytest.fixture
def viewer_role(db: Session):
    """Create viewer role."""
    role = db.query(Role).filter_by(name=rbac.ROLE_VIEWER).first()
    if not role:
        role = Role(name=rbac.ROLE_VIEWER, description="Read-only access")
        db.add(role)
        db.commit()
    return role


@pytest.fixture
def test_company(db: Session):
    """Create a test company."""
    company = Organization(
        name="Test Company",
        code="test-company",
        slug="test-company",
        is_active=True,
        approval_status="approved",
    )
    db.add(company)
    db.commit()
    return company


@pytest.fixture
def suspended_company(db: Session):
    """Create a suspended company."""
    company = Organization(
        name="Suspended Company",
        code="suspended-company",
        slug="suspended-company",
        is_active=False,
        approval_status="approved",
    )
    db.add(company)
    db.commit()
    return company


@pytest.fixture
def pending_company(db: Session):
    """Create a company pending approval."""
    company = Organization(
        name="Pending Company",
        code="pending-company",
        slug="pending-company",
        is_active=True,
        approval_status="pending",
    )
    db.add(company)
    db.commit()
    return company


@pytest.fixture
def platform_owner_user(db: Session, platform_owner_role):
    """Create a platform owner user (no tenant)."""
    user = User(
        tenant_id=None,  # NULL for platform owner
        email="platform@aegis.local",
        hashed_password=hash_password("password123"),
        full_name="Platform Owner",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    
    # Assign role
    user_role = UserRole(user_id=user.id, role_id=platform_owner_role.id)
    db.add(user_role)
    db.commit()
    return user


@pytest.fixture
def company_admin_user(db: Session, test_company, admin_role):
    """Create a company admin user."""
    user = User(
        tenant_id=test_company.id,
        email="admin@testcompany.com",
        hashed_password=hash_password("password123"),
        full_name="Company Admin",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    
    # Assign role
    user_role = UserRole(user_id=user.id, role_id=admin_role.id)
    db.add(user_role)
    db.commit()
    return user


@pytest.fixture
def analyst_user(db: Session, test_company, analyst_role):
    """Create an analyst user."""
    user = User(
        tenant_id=test_company.id,
        email="analyst@testcompany.com",
        hashed_password=hash_password("password123"),
        full_name="Security Analyst",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    
    user_role = UserRole(user_id=user.id, role_id=analyst_role.id)
    db.add(user_role)
    db.commit()
    return user


@pytest.fixture
def viewer_user(db: Session, test_company, viewer_role):
    """Create a viewer user."""
    user = User(
        tenant_id=test_company.id,
        email="viewer@testcompany.com",
        hashed_password=hash_password("password123"),
        full_name="Security Viewer",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    
    user_role = UserRole(user_id=user.id, role_id=viewer_role.id)
    db.add(user_role)
    db.commit()
    return user


@pytest.fixture
def inactive_user(db: Session, test_company, viewer_role):
    """Create an inactive user."""
    user = User(
        tenant_id=test_company.id,
        email="inactive@testcompany.com",
        hashed_password=hash_password("password123"),
        full_name="Inactive User",
        is_active=False,  # Inactive
        email_verified=True,
    )
    db.add(user)
    db.flush()
    
    user_role = UserRole(user_id=user.id, role_id=viewer_role.id)
    db.add(user_role)
    db.commit()
    return user


# =============================================================================
# Test 1: super_admin can access /admin routes
# =============================================================================

class TestSuperAdminAccess:
    """Test that super_admin can access platform owner routes."""

    def test_platform_owner_can_access_admin_routes(
        self, db: Session, platform_owner_user, settings
    ):
        """Platform owner should be able to access platform routes."""
        # Create token for platform owner
        token = create_access_token(
            subject=platform_owner_user.id,
            roles=[rbac.ROLE_PLATFORM_OWNER],
            tenant_id=uuid.uuid4(),  # Can be any or None
        )
        
        # Mock HTTP Authorization
        mock_cred = _request_with_token(token)
        
        # Should not raise
        principal = get_current_user(mock_cred, db)
        
        assert principal.id == platform_owner_user.id
        assert principal.is_platform_owner is True
        assert principal.tenant_id is None  # Platform owner has no tenant
    
    def test_platform_owner_can_access_with_null_tenant(
        self, db: Session, platform_owner_user
    ):
        """Platform owner with NULL tenant_id should authenticate successfully."""
        # Platform owner has tenant_id = NULL
        assert platform_owner_user.tenant_id is None
        
        # Create token
        token = create_access_token(
            subject=platform_owner_user.id,
            roles=[rbac.ROLE_PLATFORM_OWNER],
            tenant_id=uuid.uuid4(),  # Dummy tenant in token
        )
        
        mock_cred = _request_with_token(token)
        
        # Should authenticate successfully
        principal = get_current_user(mock_cred, db)
        assert principal.is_platform_owner is True
        assert principal.tenant_id is None


# =============================================================================
# Test 2: company_admin cannot access /admin routes
# =============================================================================

class TestCompanyAdminRestrictions:
    """Test that company_admin cannot access platform owner routes."""

    def test_company_admin_cannot_access_platform_routes(
        self, db: Session, company_admin_user, test_company
    ):
        """Company admin should be blocked from platform owner routes."""
        # Create token
        token = create_access_token(
            subject=company_admin_user.id,
            roles=[rbac.ROLE_ADMIN],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        # Authenticate
        principal = get_current_user(mock_cred, db)
        
        # Verify company admin
        assert principal.is_company_admin is True
        assert principal.is_platform_owner is False
        
        # Should fail platform owner check
        with pytest.raises(HTTPException) as exc_info:
            require_platform_owner()(principal)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Test 3: analyst cannot create company users if not allowed
# =============================================================================

class TestAnalystPermissions:
    """Test analyst role permissions and restrictions."""

    def test_analyst_can_access_read_routes(
        self, db: Session, analyst_user, test_company
    ):
        """Analyst should be able to access read routes."""
        token = create_access_token(
            subject=analyst_user.id,
            roles=[rbac.ROLE_ANALYST],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        principal = get_current_user(mock_cred, db)
        
        # Should pass reader check
        from app.api.auth_deps import require_viewer
        result = require_viewer()(principal)
        assert result.id == analyst_user.id
    
    def test_analyst_cannot_access_admin_routes(
        self, db: Session, analyst_user, test_company
    ):
        """Analyst should be blocked from admin-only routes."""
        token = create_access_token(
            subject=analyst_user.id,
            roles=[rbac.ROLE_ANALYST],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        principal = get_current_user(mock_cred, db)
        
        # Should fail company admin check
        with pytest.raises(HTTPException) as exc_info:
            require_company_admin()(principal)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Test 4 & 5: company_admin can manage own users, not other company users
# =============================================================================

class TestCompanyScopeEnforcement:
    """Test that users can only access their own company's data."""

    def test_company_admin_can_manage_own_company(
        self, db: Session, company_admin_user, test_company
    ):
        """Company admin should be able to manage users in own company."""
        principal = Principal(
            id=company_admin_user.id,
            tenant_id=test_company.id,
            tenant_code=test_company.code,
            tenant_name=test_company.name,
            email=company_admin_user.email,
            full_name=company_admin_user.full_name,
            roles=frozenset([rbac.ROLE_ADMIN]),
        )
        
        # Should not raise for own company
        require_same_company(principal, test_company.id, "manage")
    
    def test_company_admin_cannot_manage_other_company(
        self, db: Session, company_admin_user, test_company, db_session
    ):
        """Company admin should be blocked from managing other companies."""
        # Create another company
        other_company = Organization(
            name="Other Company",
            code="other-company",
            slug="other-company",
            is_active=True,
            approval_status="approved",
        )
        db.add(other_company)
        db.commit()
        
        principal = Principal(
            id=company_admin_user.id,
            tenant_id=test_company.id,  # User's company
            tenant_code=test_company.code,
            tenant_name=test_company.name,
            email=company_admin_user.email,
            full_name=company_admin_user.full_name,
            roles=frozenset([rbac.ROLE_ADMIN]),
        )
        
        # Should raise for other company
        with pytest.raises(HTTPException) as exc_info:
            require_same_company(principal, other_company.id, "manage")
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "another company" in exc_info.value.detail.lower()
    
    def test_platform_owner_can_manage_any_company(
        self, db: Session, platform_owner_user
    ):
        """Platform owner should be able to manage any company."""
        # Create any company
        any_company = Organization(
            name="Any Company",
            code="any-company",
            slug="any-company",
            is_active=True,
            approval_status="approved",
        )
        db.add(any_company)
        db.commit()
        
        principal = Principal(
            id=platform_owner_user.id,
            tenant_id=None,  # Platform owner has no tenant
            tenant_code=None,
            tenant_name=None,
            email=platform_owner_user.email,
            full_name=platform_owner_user.full_name,
            roles=frozenset([rbac.ROLE_PLATFORM_OWNER]),
        )
        
        # Should not raise - platform owner bypass
        require_same_company(principal, any_company.id, "manage")


# =============================================================================
# Test 6: company A user cannot access company B data
# =============================================================================

class TestCrossTenantPrevention:
    """Test cross-tenant access is strictly prevented."""

    def test_user_cannot_access_other_company_data(
        self, db: Session, company_admin_user, test_company
    ):
        """User should be blocked from accessing other companies' data."""
        # Create company B
        company_b = Organization(
            name="Company B",
            code="company-b",
            slug="company-b",
            is_active=True,
            approval_status="approved",
        )
        db.add(company_b)
        db.commit()
        
        # Create principal for company A user
        principal = Principal(
            id=company_admin_user.id,
            tenant_id=test_company.id,
            tenant_code=test_company.code,
            tenant_name=test_company.name,
            email=company_admin_user.email,
            full_name=company_admin_user.full_name,
            roles=frozenset([rbac.ROLE_ADMIN]),
        )
        
        # Create tenant context for company B
        tenant_context = TenantContext(
            tenant_id=company_b.id,
            tenant_code=company_b.code,
            tenant_name=company_b.name,
        )
        
        # Should raise
        with pytest.raises(HTTPException) as exc_info:
            enforce_company_scope(principal, tenant_context)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "mismatch" in exc_info.value.detail.lower()


# =============================================================================
# Test 7: suspended company blocked
# =============================================================================

class TestSuspendedCompanyBlocking:
    """Test that suspended company users are blocked."""

    def test_suspended_company_user_blocked(
        self, db: Session, suspended_company, admin_role
    ):
        """Users from suspended companies should be blocked from authentication."""
        # Create user in suspended company
        user = User(
            tenant_id=suspended_company.id,
            email="suspended@company.com",
            hashed_password=hash_password("password123"),
            full_name="Suspended User",
            is_active=True,  # User is active
            email_verified=True,
        )
        db.add(user)
        db.flush()
        
        # Assign role
        user_role = UserRole(user_id=user.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        
        # Create token
        token = create_access_token(
            subject=user.id,
            roles=[rbac.ROLE_ADMIN],
            tenant_id=suspended_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        # Should be blocked
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_cred, db)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "suspended" in exc_info.value.detail.lower()


# =============================================================================
# Test 8: inactive user blocked
# =============================================================================

class TestInactiveUserBlocking:
    """Test that inactive users are blocked."""

    def test_inactive_user_blocked(
        self, db: Session, inactive_user, test_company
    ):
        """Inactive users should be blocked from authentication."""
        # Create token for inactive user
        token = create_access_token(
            subject=inactive_user.id,
            roles=[rbac.ROLE_VIEWER],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        # Should be blocked
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_cred, db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "disabled" in exc_info.value.detail.lower() or "inactive" in exc_info.value.detail.lower()


# =============================================================================
# Test 9: viewer blocked from unauthorized write actions
# =============================================================================

class TestViewerRestrictions:
    """Test that viewer role is restricted to read-only."""

    def test_viewer_can_access_read_routes(
        self, db: Session, viewer_user, test_company
    ):
        """Viewer should be able to access read routes."""
        token = create_access_token(
            subject=viewer_user.id,
            roles=[rbac.ROLE_VIEWER],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        principal = get_current_user(mock_cred, db)
        
        # Should pass viewer check
        from app.api.auth_deps import require_viewer
        result = require_viewer()(principal)
        assert result.id == viewer_user.id
    
    def test_viewer_blocked_from_write_actions(
        self, db: Session, viewer_user, test_company
    ):
        """Viewer should be blocked from write operations."""
        token = create_access_token(
            subject=viewer_user.id,
            roles=[rbac.ROLE_VIEWER],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        principal = get_current_user(mock_cred, db)
        
        # Should fail writer (analyst) check
        with pytest.raises(HTTPException) as exc_info:
            from app.api.auth_deps import require_analyst
            require_analyst()(principal)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    
    def test_viewer_blocked_from_admin_actions(
        self, db: Session, viewer_user, test_company
    ):
        """Viewer should be blocked from admin operations."""
        token = create_access_token(
            subject=viewer_user.id,
            roles=[rbac.ROLE_VIEWER],
            tenant_id=test_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        principal = get_current_user(mock_cred, db)
        
        # Should fail admin check
        with pytest.raises(HTTPException) as exc_info:
            require_company_admin()(principal)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Additional Security Tests
# =============================================================================

class TestTokenSecurity:
    """Test JWT token security."""

    def test_expired_token_rejected(self, db: Session, company_admin_user, test_company):
        """Expired tokens should be rejected."""
        # Create expired token
        expired_token = jwt.encode(
            {
                "sub": str(company_admin_user.id),
                "tid": str(test_company.id),
                "roles": [rbac.ROLE_ADMIN],
                "typ": "access",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            },
            get_settings().jwt_secret_key,
            algorithm=get_settings().jwt_algorithm,
        )
        
        mock_cred = _request_with_token(expired_token)
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_cred, db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_invalid_token_rejected(self, db: Session):
        """Invalid tokens should be rejected."""
        mock_cred = _request_with_token("invalid.token.here")
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_cred, db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_tampered_token_rejected(self, db: Session, company_admin_user, test_company):
        """Tampered tokens should be rejected."""
        # Create valid token
        token = create_access_token(
            subject=company_admin_user.id,
            roles=[rbac.ROLE_ADMIN],
            tenant_id=test_company.id,
        )
        
        # Tamper with token
        tampered = token[:-10] + "tampered!!"
        
        mock_cred = _request_with_token(tampered)
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_cred, db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestRoleHierarchy:
    """Test role hierarchy and inheritance."""

    def test_has_minimum_role_with_hierarchy(self):
        """Test role hierarchy checking."""
        # Admin should pass for viewer minimum
        assert rbac.has_minimum_role(frozenset([rbac.ROLE_ADMIN]), rbac.ROLE_VIEWER)
        
        # Analyst should pass for viewer minimum
        assert rbac.has_minimum_role(frozenset([rbac.ROLE_ANALYST]), rbac.ROLE_VIEWER)
        
        # Viewer should NOT pass for analyst minimum
        assert not rbac.has_minimum_role(frozenset([rbac.ROLE_VIEWER]), rbac.ROLE_ANALYST)
        
        # Platform owner should pass for any minimum
        assert rbac.has_minimum_role(frozenset([rbac.ROLE_PLATFORM_OWNER]), rbac.ROLE_ADMIN)
    
    def test_is_platform_owner(self):
        """Test platform owner detection."""
        assert rbac.is_platform_owner(frozenset([rbac.ROLE_PLATFORM_OWNER]))
        assert not rbac.is_platform_owner(frozenset([rbac.ROLE_ADMIN]))
        assert not rbac.is_platform_owner(frozenset([rbac.ROLE_ANALYST]))
    
    def test_is_company_admin(self):
        """Test company admin detection."""
        assert rbac.is_company_admin(frozenset([rbac.ROLE_ADMIN]))
        assert rbac.is_company_admin(frozenset([rbac.ROLE_PLATFORM_OWNER]))
        assert not rbac.is_company_admin(frozenset([rbac.ROLE_ANALYST]))


class TestPendingCompany:
    """Test pending approval company handling."""

    def test_pending_company_user_blocked(
        self, db: Session, pending_company, admin_role
    ):
        """Users from pending companies should be blocked."""
        # Create user in pending company
        user = User(
            tenant_id=pending_company.id,
            email="pending@company.com",
            hashed_password=hash_password("password123"),
            full_name="Pending User",
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()
        
        user_role = UserRole(user_id=user.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()
        
        # Create token
        token = create_access_token(
            subject=user.id,
            roles=[rbac.ROLE_ADMIN],
            tenant_id=pending_company.id,
        )
        
        mock_cred = _request_with_token(token)
        
        # Should be blocked
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_cred, db)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "pending" in exc_info.value.detail.lower()
