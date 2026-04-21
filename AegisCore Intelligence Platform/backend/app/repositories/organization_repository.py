from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.oltp import Organization, User, OrganizationInvitation


class OrganizationRepository:
    """Repository for organization/tenant operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def get_by_code(self, code: str) -> Organization | None:
        normalized = code.strip().lower()
        stmt = select(Organization).where(func.lower(Organization.code) == normalized)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        self.db.refresh(organization)
        return organization

    def list(self, *, limit: int, offset: int) -> tuple[list[Organization], int]:
        """List all organizations."""
        total = self.db.scalar(select(func.count()).select_from(Organization)) or 0
        stmt = (
            select(Organization)
            .order_by(Organization.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = self.db.execute(stmt).scalars().all()
        return rows, int(total)

    def list_by_approval_status(
        self, *, status: str, limit: int, offset: int
    ) -> tuple[list[Organization], int]:
        """List organizations filtered by approval status."""
        base_query = select(Organization).where(Organization.approval_status == status)
        total = self.db.scalar(
            select(func.count()).select_from(base_query.subquery())
        ) or 0
        stmt = (
            base_query
            .order_by(Organization.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = self.db.execute(stmt).scalars().all()
        return rows, int(total)

    def get_user_count(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(User).where(User.tenant_id == organization_id)
        return self.db.scalar(stmt) or 0

    def update(self, organization: Organization) -> Organization:
        self.db.flush()
        self.db.refresh(organization)
        return organization

    def get_platform_stats(self) -> dict[str, int]:
        """Get platform-wide statistics including approval metrics."""
        total_tenants = self.db.scalar(select(func.count()).select_from(Organization)) or 0
        active_tenants = self.db.scalar(
            select(func.count()).select_from(Organization).where(Organization.is_active == True)
        ) or 0
        pending_tenants = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.approval_status == "pending")
        ) or 0
        rejected_tenants = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.approval_status == "rejected")
        ) or 0
        total_users = self.db.scalar(select(func.count()).select_from(User)) or 0
        return {
            "total_tenants": int(total_tenants),
            "active_tenants": int(active_tenants),
            "pending_tenants": int(pending_tenants),
            "rejected_tenants": int(rejected_tenants),
            "total_users": int(total_users),
        }

    def get_company_admins(self, organization_id: uuid.UUID) -> list[User]:
        """Get all admin users for a company."""
        from app.core import rbac
        from app.models.oltp import UserRole, Role

        stmt = (
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(User.tenant_id == organization_id)
            .where(Role.name == rbac.ROLE_ADMIN)
            .where(User.is_active == True)
            .options(joinedload(User.roles).joinedload(UserRole.role))
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_detailed_platform_metrics(self) -> dict[str, int]:
        """Get comprehensive platform metrics for dashboard."""
        # Tenant metrics
        total_tenants = self.db.scalar(select(func.count()).select_from(Organization)) or 0
        active_tenants = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.is_active == True, Organization.approval_status == "approved")
        ) or 0
        pending_tenants = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.approval_status == "pending")
        ) or 0
        rejected_tenants = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.approval_status == "rejected")
        ) or 0
        suspended_tenants = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.is_active == False)
        ) or 0

        # User metrics
        total_users = self.db.scalar(select(func.count()).select_from(User)) or 0
        active_users = self.db.scalar(
            select(func.count()).select_from(User).where(User.is_active == True)
        ) or 0
        inactive_users = total_users - active_users

        # Invitation metrics
        total_invitations = self.db.scalar(
            select(func.count()).select_from(OrganizationInvitation)
        ) or 0
        pending_invitations = self.db.scalar(
            select(func.count())
            .select_from(OrganizationInvitation)
            .where(OrganizationInvitation.accepted_at == None)
            .where(OrganizationInvitation.expires_at > datetime.now(timezone.utc))
        ) or 0
        accepted_invitations = self.db.scalar(
            select(func.count())
            .select_from(OrganizationInvitation)
            .where(OrganizationInvitation.accepted_at != None)
        ) or 0
        expired_invitations = self.db.scalar(
            select(func.count())
            .select_from(OrganizationInvitation)
            .where(OrganizationInvitation.expires_at <= datetime.now(timezone.utc))
            .where(OrganizationInvitation.accepted_at == None)
        ) or 0

        # Recent signups
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

        recent_7d = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.created_at >= seven_days_ago)
        ) or 0
        recent_30d = self.db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.created_at >= thirty_days_ago)
        ) or 0

        return {
            "total_tenants": int(total_tenants),
            "active_tenants": int(active_tenants),
            "pending_tenants": int(pending_tenants),
            "rejected_tenants": int(rejected_tenants),
            "suspended_tenants": int(suspended_tenants),
            "total_users": int(total_users),
            "active_users": int(active_users),
            "inactive_users": int(inactive_users),
            "total_invitations_sent": int(total_invitations),
            "pending_invitations": int(pending_invitations),
            "accepted_invitations": int(accepted_invitations),
            "expired_invitations": int(expired_invitations),
            "recent_signups_7d": int(recent_7d),
            "recent_signups_30d": int(recent_30d),
            "logins_today": 0,  # Placeholder - would need analytics tracking
            "logins_this_week": 0,  # Placeholder - would need analytics tracking
        }
