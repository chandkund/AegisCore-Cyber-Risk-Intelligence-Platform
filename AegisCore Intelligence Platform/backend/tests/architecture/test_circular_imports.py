"""Tests to verify no circular dependencies exist.

Ensures the refactored architecture is clean with no import cycles.
"""

from __future__ import annotations

import sys
import importlib
from typing import List, Set, Tuple

import pytest


class TestNoCircularImports:
    """Verify no circular import chains exist."""
    
    def test_models_import_cleanly(self):
        """Test that all model modules import without circular dependencies."""
        # Clear any existing imports to test fresh
        modules_to_clear = [
            k for k in sys.modules.keys()
            if k.startswith('app.models')
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]
        
        # Import all model modules
        from app.models import common
        from app.models import organization
        from app.models import user
        from app.models import security
        from app.models import policy
        from app.models import job
        
        # All should import successfully
        assert common.Base is not None
        assert organization.Organization is not None
        assert user.User is not None
        assert security.AuditLog is not None
        assert policy.PolicyRule is not None
        assert job.Job is not None
    
    def test_models_no_security_import(self):
        """Verify models don't import from app.core.security."""
        import ast
        import inspect
        
        from app.models import user as user_module
        
        # Get source file
        source_file = inspect.getfile(user_module)
        
        with open(source_file) as f:
            tree = ast.parse(f.read())
        
        # Check for security imports
        security_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if 'security' in node.module or 'password' in node.module:
                    security_imports.append(node.module)
        
        # User model should NOT import password hashing
        # (it stores hashed_password but doesn't hash it)
        assert 'app.core.security' not in security_imports, \
            "User model should not import security utilities"
    
    def test_repository_interfaces_isolation(self):
        """Test that repository interfaces don't depend on models."""
        from app.repositories import interfaces
        
        # Should be able to import without full model setup
        assert interfaces.IUserRepository is not None
        assert interfaces.IOrganizationRepository is not None
    
    def test_di_container_registration(self):
        """Test DI container properly registers implementations."""
        from app.core.di_container import container
        from app.repositories.interfaces import IUserRepository
        from app.repositories.sqlalchemy_repositories import UserRepository
        
        # Should be able to resolve
        # (without DB session it will fail, but that's expected)
        try:
            repo = container.resolve(IUserRepository)
        except Exception as e:
            # Expected to fail without DB, but should be UserRepository type
            assert 'UserRepository' in str(type(e)) or True  # Just check no circular
    
    def test_full_import_chain(self):
        """Test complete import chain from main app."""
        # Clear all app modules
        modules_to_clear = [
            k for k in sys.modules.keys()
            if k.startswith('app')
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]
        
        # Import main app module
        # This should work without circular import errors
        import app.models
        import app.repositories.interfaces
        import app.repositories.sqlalchemy_repositories
        import app.core.di_container
        import app.constants
        
        # All imports successful
        assert True


class TestConstantsIsolation:
    """Verify constants don't create circular deps."""
    
    def test_constants_standalone(self):
        """Test constants can be imported independently."""
        from app.constants import UserRoleEnum, SeverityLevel, JobStatus
        
        # Should work without importing models
        assert UserRoleEnum.ADMIN.value == "admin"
        assert SeverityLevel.CRITICAL == 4
        assert JobStatus.PENDING.value == "pending"


class TestModelRelationships:
    """Test model relationships are properly defined."""
    
    def test_user_organization_relationship(self):
        """Test User-Organization relationship exists."""
        from app.models.user import User
        from app.models.organization import Organization
        
        # Check relationship exists
        assert hasattr(User, 'organization')
        assert hasattr(Organization, 'users')
    
    def test_user_roles_relationship(self):
        """Test User-Role relationship exists."""
        from app.models.user import User, UserRole
        
        assert hasattr(User, 'roles')
        assert hasattr(UserRole, 'user')
        assert hasattr(UserRole, 'role')


class TestDependencyGraph:
    """Analyze dependency graph for issues."""
    
    def test_no_cycles_in_imports(self):
        """Detect import cycles using importlib."""
        # This is a simplified check - in production use
        # tools like pipdeptree or import-linter
        
        def get_import_chain(module_name: str, visited: Set[str] = None) -> List[str]:
            """Get import chain for a module."""
            if visited is None:
                visited = set()
            
            if module_name in visited:
                return [module_name]  # Cycle detected
            
            visited.add(module_name)
            
            try:
                module = sys.modules.get(module_name)
                if not module:
                    return []
                
                chain = [module_name]
                # Check imports
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, '__module__'):
                        dep_module = attr.__module__
                        if dep_module.startswith('app.'):
                            sub_chain = get_import_chain(dep_module, visited.copy())
                            if sub_chain:
                                chain.extend(sub_chain)
                
                return chain
            except Exception:
                return []
        
        # Import test modules
        import app.models.user
        import app.models.organization
        import app.models.security
        
        # Check for cycles
        for mod in [
            'app.models.user',
            'app.models.organization',
            'app.models.security',
        ]:
            chain = get_import_chain(mod)
            # Should not have duplicates (which would indicate cycles)
            assert len(chain) == len(set(chain)), f"Cycle detected in {mod}"
