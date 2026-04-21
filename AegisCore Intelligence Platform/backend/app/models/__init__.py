"""ORM models: import side effects register metadata with Base.

Refactored from single god-class (oltp.py) into clean, focused modules:
- common: Base class and mixins
- user: User, Role, authentication
- organization: Organization, BusinessUnit, Team
- security: AuditLog, SecurityEvent
- policy: PolicyRule, ComplianceFramework
- job: Job, ScheduledJob

Each module has no circular dependencies with security utilities.
"""

# Import order matters for SQLAlchemy metadata registration
# 1. Common base first
from app.models import common  # noqa: F401

# 2. Independent models (no foreign keys)
from app.models import organization  # noqa: F401

# 3. Models with relationships
from app.models import user  # noqa: F401
from app.models import security  # noqa: F401
from app.models import policy  # noqa: F401
from app.models import job  # noqa: F401

# 4. Legacy modules (to be migrated)
from app.models import email_verification  # noqa: F401
from app.models import oltp  # noqa: F401 - deprecated, use split modules above
from app.models import reporting  # noqa: F401

# Clean exports
from app.models.common import Base
from app.models.user import User, Role, UserRole, EmailVerificationOTP
from app.models.organization import Organization, BusinessUnit, Team
from app.models.security import AuditLog, SecurityEvent, PasswordResetToken
from app.models.policy import PolicyRule, PolicyViolation, ComplianceFramework
from app.models.job import Job, JobLog, ScheduledJob

__all__ = [
    # Base
    "Base",
    # User & Auth
    "User",
    "Role",
    "UserRole",
    "EmailVerificationOTP",
    # Organization
    "Organization",
    "BusinessUnit",
    "Team",
    # Security
    "AuditLog",
    "SecurityEvent",
    "PasswordResetToken",
    # Policy
    "PolicyRule",
    "PolicyViolation",
    "ComplianceFramework",
    # Jobs
    "Job",
    "JobLog",
    "ScheduledJob",
    # Legacy
    "email_verification",
    "oltp",
    "reporting",
]
