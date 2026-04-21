# AegisCore Backend Architecture

Clean Architecture Refactoring Summary

## 1. New Structure

```
backend/
├── app/
│   ├── constants/           # All enums and constants
│   │   └── __init__.py     # UserRoleEnum, SeverityLevel, etc.
│   │
│   ├── models/             # Split models (no god class)
│   │   ├── __init__.py     # Clean exports
│   │   ├── common.py       # Base class, mixins
│   │   ├── user.py         # User, Role, UserRole
│   │   ├── organization.py # Organization, BusinessUnit, Team
│   │   ├── security.py     # AuditLog, SecurityEvent
│   │   ├── policy.py       # PolicyRule, PolicyViolation
│   │   ├── job.py          # Job, JobLog, ScheduledJob
│   │   └── oltp.py         # Deprecated (legacy compatibility)
│   │
│   ├── repositories/       # Repository Pattern
│   │   ├── __init__.py
│   │   ├── interfaces.py   # IUserRepository, IJobRepository, etc.
│   │   └── sqlalchemy_repositories.py  # Concrete implementations
│   │
│   ├── core/               # Dependency Injection
│   │   └── di_container.py # DI container and registration
│   │
│   └── ...
│
└── tests/
    └── architecture/
        └── test_circular_imports.py  # Verification tests
```

## 2. Files Changed

### New Files Created:
- `app/constants/__init__.py` - All constants and enums
- `app/models/common.py` - Base class and mixins
- `app/models/user.py` - User model (circular dependency removed)
- `app/models/organization.py` - Organization models
- `app/models/security.py` - Security models
- `app/models/policy.py` - Policy models
- `app/models/job.py` - Job models
- `app/repositories/interfaces.py` - Repository interfaces
- `app/repositories/sqlalchemy_repositories.py` - SQLAlchemy implementations
- `app/core/di_container.py` - Dependency injection container
- `tests/architecture/test_circular_imports.py` - Verification tests

### Modified Files:
- `app/models/__init__.py` - Updated to import all new modules
- `app/models/oltp.py` - Deprecated (kept for backward compatibility)

## 3. Key Refactoring Changes

### Before:
```python
# oltp.py - 744 lines God class
class User(Base):
    # ... imports from app.core.security (CIRCULAR!)
    from app.core.security import hash_password
    
    def set_password(self, password):
        self.hashed_password = hash_password(password)  # ❌ Circular
```

### After:
```python
# user.py - Clean model, no security imports
class User(Base):
    hashed_password: Mapped[str]  # Just storage
    
    # No password hashing here!
    # Hashing done in UserService

# user_service.py - Handles password operations
class UserService:
    from app.core.security import hash_password  # ✅ OK here
    
    def create_user(self, email, password):
        hashed = hash_password(password)
        return User(email=email, hashed_password=hashed)
```

## 4. Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                         API Layer                            │
└───────────────────────┬─────────────────────────────────────┘
                        │ uses
┌───────────────────────▼─────────────────────────────────────┐
│                   Services Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │UserService   │  │JobService    │  │AuditService │        │
│  │- hash_password│  │- process_jobs│  │- log_events │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────┬─────────────────────────────────────┘
                        │ uses (via DI)
┌───────────────────────▼─────────────────────────────────────┐
│              Repository Layer (Interfaces)                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │IUserRepository     │IJobRepository  │IAuditRepository │  │
│  │- get_by_id()       │- get_by_id()   │- get_by_id()    │  │
│  │- get_by_email()    │- get_by_tenant │- get_by_action() │  │
│  │- create()          │- create()      │- create()        │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ implements
┌───────────────────────▼─────────────────────────────────────┐
│           Repository Layer (SQLAlchemy)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │UserRepository│  │JobRepository │  │AuditRepository│        │
│  │(SQLA impl)   │  │(SQLA impl)   │  │(SQLA impl)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└───────────────────────┬─────────────────────────────────────┘
                        │ uses
┌───────────────────────▼─────────────────────────────────────┐
│                     Models Layer                              │
│                                                               │
│   ┌─────────┐  ┌─────────────┐  ┌────────────┐  ┌────────┐   │
│   │common   │  │user         │  │organization│  │security│   │
│   │.Base    │──│.User        │──│.Organization│  │.AuditLog│   │
│   │.Mixins │  │.Role        │  │.Team       │  │.Security│   │
│   └─────────┘  └─────────────┘  └────────────┘  └────────┘   │
│                         │                                     │
│   ┌─────────┐  ┌─────────────┐                               │
│   │policy   │  │job          │                               │
│   │.Policy  │  │.Job         │                               │
│   │.Violation│  │.JobLog      │                               │
│   └─────────┘  └─────────────┘                               │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## 5. Final Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                           FastAPI Application                         │
├────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                     API Endpoints                               │  │
│  │  auth.py  │  users.py  │  jobs.py  │  findings.py  │ ...      │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │                   Pydantic Schemas                                │  │
│  │  UserCreate  │  JobOut  │  FindingOut  │  Paginated[T]          │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │                   Service Layer                                   │  │
│  │  UserService  │  JobService  │  AuditService  │  CacheService   │  │
│  │  - Password ops     - Job queue    - Event logging   - Redis      │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │              Repository Interfaces (ABC)                        │  │
│  │  IUserRepository  │  IJobRepository  │  IAuditRepository         │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │         Repository Implementations (SQLAlchemy)                 │  │
│  │  UserRepository  │  JobRepository  │  AuditRepository         │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │                        Models                                    │  │
│  │  User  │  Organization  │  Job  │  AuditLog  │  PolicyRule     │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │                  SQLAlchemy ORM                                   │  │
│  │  Engine  │  Session  │  Query  │  selectinload  │  joinedload │  │
│  └─────────────────────┬──────────────────────────────────────────┘  │
│                        │                                             │
│  ┌─────────────────────▼──────────────────────────────────────────┐  │
│  │                    PostgreSQL                                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │  │
│  │  │  users   │  │  orgs    │  │  jobs    │  │  audit   │       │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

## 6. Key Improvements

### ✅ Code Smells Eliminated:

| Smell | Before | After |
|-------|--------|-------|
| **God Class** | oltp.py (744 lines) | 6 focused modules (avg 100 lines) |
| **Circular Dependency** | models ↔ security | Clean separation, no cycles |
| **Tight Coupling** | Direct model imports everywhere | Repository Pattern + DI |
| **Magic Numbers** | Hardcoded strings/numbers | app/constants enums |
| **No Abstraction** | Concrete SQLA everywhere | Interface-based repositories |

### ✅ New Capabilities:

1. **Easy Testing**: Mock repositories for unit tests
2. **Swappable Implementations**: Cache layer, different DB
3. **Clean Imports**: No import cycles, faster startup
4. **Type Safety**: Enums prevent invalid values
5. **Future-Proof**: Add new models without touching existing code

## 7. Running Verification

```bash
# Run circular import tests
cd backend
pytest tests/architecture/test_circular_imports.py -v

# Run all tests
pytest

# Check for cycles with import-linter (optional)
pip install import-linter
lint-imports
```

## 8. Migration Guide

### For existing code using old oltp.py:

```python
# Old way (still works for backward compatibility)
from app.models.oltp import User

# New recommended way
from app.models.user import User
from app.models import User  # Also works via __init__.py

# Using repositories (new)
from app.core.di_container import container
from app.repositories.interfaces import IUserRepository

user_repo = container.resolve(IUserRepository)
user = user_repo.get_by_email("user@example.com")
```

---

**Architecture refactoring complete!** 🎉
