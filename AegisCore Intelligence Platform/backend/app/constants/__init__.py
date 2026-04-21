"""Application constants and enums.

Centralizes all magic numbers, string constants, and enums
for type safety and maintainability.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Final


# ============================================================================
# USER & AUTHENTICATION
# ============================================================================

class UserRoleEnum(str, Enum):
    """User role definitions."""
    PLATFORM_OWNER = "platform_owner"
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class UserStatusEnum(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"


# Password policy constants
MIN_PASSWORD_LENGTH: Final[int] = 12
MAX_PASSWORD_LENGTH: Final[int] = 128
MAX_FAILED_LOGIN_ATTEMPTS: Final[int] = 5
LOCKOUT_DURATION_MINUTES: Final[int] = 30


# ============================================================================
# SECURITY & VULNERABILITY
# ============================================================================

class SeverityLevel(IntEnum):
    """Vulnerability severity levels."""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    INFO = 0


class FindingStatus(str, Enum):
    """Finding remediation status."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ACCEPTED_RISK = "ACCEPTED_RISK"


class AssetCriticality(IntEnum):
    """Asset criticality levels."""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


# ============================================================================
# JOBS & PROCESSING
# ============================================================================

class JobStatus(str, Enum):
    """Background job status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobKind(str, Enum):
    """Types of background jobs."""
    UPLOAD_PROCESSING = "upload_processing"
    REPORT_GENERATION = "report_generation"
    DATA_IMPORT = "data_import"
    SCAN_EXECUTION = "scan_execution"
    NOTIFICATION_SEND = "notification_send"


# ============================================================================
# POLICY & COMPLIANCE
# ============================================================================

class PolicyRuleType(str, Enum):
    """Policy rule types."""
    SEVERITY_THRESHOLD = "severity_threshold"
    SLA_COMPLIANCE = "sla_compliance"
    APPROVER_REQUIRED = "approver_required"
    AUTO_ASSIGN = "auto_assign"


class ComplianceStatus(str, Enum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    EXEMPTED = "exempted"


# ============================================================================
# PAGINATION & API
# ============================================================================

DEFAULT_PAGE_SIZE: Final[int] = 50
MAX_PAGE_SIZE: Final[int] = 200
DEFAULT_OFFSET: Final[int] = 0


# ============================================================================
# FILE UPLOADS
# ============================================================================

MAX_FILE_SIZE_BYTES: Final[int] = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".csv", ".json", ".xml", ".nessus", ".sarif", ".pdf", ".zip"
})


# ============================================================================
# CACHE TTLs (seconds)
# ============================================================================

CACHE_TTL_SHORT: Final[int] = 60       # 1 minute
CACHE_TTL_MEDIUM: Final[int] = 300     # 5 minutes
CACHE_TTL_LONG: Final[int] = 1800      # 30 minutes
CACHE_TTL_VERY_LONG: Final[int] = 86400  # 24 hours


# ============================================================================
# DATABASE
# ============================================================================

# Connection pool settings
DB_POOL_SIZE: Final[int] = 20
DB_MAX_OVERFLOW: Final[int] = 30
DB_POOL_TIMEOUT: Final[int] = 30
DB_POOL_RECYCLE: Final[int] = 1800


# ============================================================================
# AUDIT LOGGING
# ============================================================================

class AuditAction(str, Enum):
    """Audit log action types."""
    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    MFA_SUCCESS = "mfa_success"
    MFA_FAILURE = "mfa_failure"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    
    # User Management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_DISABLE = "user_disable"
    USER_ENABLE = "user_enable"
    
    # Data Operations
    FILE_UPLOAD = "file_upload"
    FILE_DELETE = "file_delete"
    FINDING_CREATE = "finding_create"
    FINDING_UPDATE = "finding_update"
    FINDING_DELETE = "finding_delete"
    
    # Security Events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_HIT = "rate_limit_hit"
    CSRF_VIOLATION = "csrf_violation"


# ============================================================================
# HTTP STATUS MESSAGES
# ============================================================================

RATE_LIMIT_EXCEEDED: Final[str] = "Rate limit exceeded. Please try again later."
INVALID_CREDENTIALS: Final[str] = "Invalid email or password."
ACCOUNT_LOCKED: Final[str] = "Account temporarily locked due to multiple failed attempts."
INSUFFICIENT_PERMISSIONS: Final[str] = "You do not have permission to perform this action."
RESOURCE_NOT_FOUND: Final[str] = "The requested resource was not found."
