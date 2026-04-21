from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TenantOut(BaseModel):
    id: str
    name: str
    code: str
    is_active: bool
    approval_status: str
    created_at: datetime


class TenantUpdate(BaseModel):
    is_active: bool | None = None
    approval_status: str | None = None
    approval_notes: str | None = None


class TenantDetailOut(BaseModel):
    id: str
    name: str
    code: str
    is_active: bool
    approval_status: str
    approval_notes: str | None
    approved_at: datetime | None
    approved_by: str | None
    created_at: datetime
    user_count: int


class PlatformStatsOut(BaseModel):
    total_tenants: int
    active_tenants: int
    pending_tenants: int
    rejected_tenants: int
    total_users: int


class TenantCreate(BaseModel):
    """Schema for platform owner to manually create a company."""
    name: str = Field(..., min_length=2, max_length=200)
    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    admin_email: str = Field(..., max_length=254)
    admin_full_name: str = Field(..., min_length=2, max_length=200)
    admin_password: str = Field(..., min_length=8)
    approval_status: str = Field(default="approved")
    is_active: bool = Field(default=True)


class TenantAdminOut(BaseModel):
    """Company admin user information for platform owner view."""
    id: str
    email: str
    full_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    last_login_at: datetime | None = None


class TenantWithAdminsOut(TenantDetailOut):
    """Tenant detail including admin users."""
    admins: list[TenantAdminOut]


class AdminPasswordReset(BaseModel):
    """Schema for platform owner to reset company admin password."""
    new_password: str = Field(..., min_length=8)
    require_password_change: bool = Field(default=True)


class PlatformMetricsOut(BaseModel):
    """Detailed platform metrics for platform owner dashboard."""
    total_tenants: int
    active_tenants: int
    pending_tenants: int
    rejected_tenants: int
    suspended_tenants: int
    total_users: int
    active_users: int
    inactive_users: int
    total_invitations_sent: int
    pending_invitations: int
    accepted_invitations: int
    expired_invitations: int
    recent_signups_7d: int
    recent_signups_30d: int
    logins_today: int = 0  # Placeholder for analytics
    logins_this_week: int = 0  # Placeholder for analytics
