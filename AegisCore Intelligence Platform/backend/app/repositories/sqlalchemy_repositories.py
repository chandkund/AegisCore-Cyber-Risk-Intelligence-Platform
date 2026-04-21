"""SQLAlchemy implementations of repository interfaces.

Concrete implementations of all repository interfaces using SQLAlchemy.
These can be swapped with other implementations (e.g., cached, mock) via DI.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User, UserRole, Role
from app.models.organization import Organization
from app.models.security import AuditLog, SecurityEvent
from app.models.job import Job
from app.models.policy import PolicyRule
from app.repositories.interfaces import (
    IUserRepository,
    IOrganizationRepository,
    IAuditLogRepository,
    IJobRepository,
    IPolicyRepository,
)
from app.constants import JobStatus


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _commit(self) -> None:
        """Commit transaction."""
        self.db.commit()
    
    def _refresh(self, obj) -> None:
        """Refresh object from database."""
        self.db.refresh(obj)


class UserRepository(BaseRepository, IUserRepository):
    """SQLAlchemy implementation of user repository."""
    
    def get_by_id(self, id: uuid.UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(func.lower(User.email) == func.lower(email))
            .first()
        )
    
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        return (
            self.db.query(User)
            .filter(User.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_active_users(self, tenant_id: uuid.UUID) -> list[User]:
        return (
            self.db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.is_active == True,
            )
            .all()
        )
    
    def search_by_name(self, tenant_id: uuid.UUID, query: str) -> list[User]:
        search = f"%{query}%"
        return (
            self.db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.full_name.ilike(search),
            )
            .all()
        )
    
    def count_by_tenant(self, tenant_id: uuid.UUID) -> int:
        return (
            self.db.query(func.count(User.id))
            .filter(User.tenant_id == tenant_id)
            .scalar()
            or 0
        )
    
    def update_last_login(self, user_id: uuid.UUID) -> None:
        user = self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            self._commit()
    
    def add_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        # Check if already has role
        exists = (
            self.db.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
            .first()
        )
        if not exists:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(user_role)
            self._commit()
    
    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        ).delete()
        self._commit()
    
    def list_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        return self.db.query(User).offset(offset).limit(limit).all()
    
    def create(self, entity: User) -> User:
        self.db.add(entity)
        self._commit()
        self._refresh(entity)
        return entity
    
    def update(self, entity: User) -> User:
        self._commit()
        self._refresh(entity)
        return entity
    
    def delete(self, id: uuid.UUID) -> bool:
        user = self.get_by_id(id)
        if user:
            self.db.delete(user)
            self._commit()
            return True
        return False


class OrganizationRepository(BaseRepository, IOrganizationRepository):
    """SQLAlchemy implementation of organization repository."""
    
    def get_by_id(self, id: uuid.UUID) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.id == id).first()
    
    def get_by_slug(self, slug: str) -> Optional[Organization]:
        return (
            self.db.query(Organization)
            .filter(Organization.slug == slug)
            .first()
        )
    
    def get_by_user(self, user_id: uuid.UUID) -> list[Organization]:
        # Get orgs where user is a member
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.tenant_id:
            org = self.get_by_id(user.tenant_id)
            return [org] if org else []
        return []
    
    def update_settings(self, org_id: uuid.UUID, settings: dict) -> Organization:
        org = self.get_by_id(org_id)
        if org:
            org.settings.update(settings)
            self._commit()
            self._refresh(org)
        return org
    
    def list_all(self, limit: int = 100, offset: int = 0) -> list[Organization]:
        return self.db.query(Organization).offset(offset).limit(limit).all()
    
    def create(self, entity: Organization) -> Organization:
        self.db.add(entity)
        self._commit()
        self._refresh(entity)
        return entity
    
    def update(self, entity: Organization) -> Organization:
        self._commit()
        self._refresh(entity)
        return entity
    
    def delete(self, id: uuid.UUID) -> bool:
        org = self.get_by_id(id)
        if org:
            self.db.delete(org)
            self._commit()
            return True
        return False


class AuditLogRepository(BaseRepository, IAuditLogRepository):
    """SQLAlchemy implementation of audit log repository."""
    
    def get_by_id(self, id: uuid.UUID) -> Optional[AuditLog]:
        return self.db.query(AuditLog).filter(AuditLog.id == id).first()
    
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_by_user(self, user_id: uuid.UUID, limit: int = 100) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.actor_user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_by_action(
        self,
        action: str,
        tenant_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        query = self.db.query(AuditLog).filter(AuditLog.action == action)
        if tenant_id:
            query = query.filter(AuditLog.tenant_id == tenant_id)
        return (
            query.order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def get_recent(self, tenant_id: uuid.UUID, minutes: int = 60) -> list[AuditLog]:
        since = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.tenant_id == tenant_id,
                AuditLog.created_at >= since,
            )
            .order_by(AuditLog.created_at.desc())
            .all()
        )
    
    def list_all(self, limit: int = 100, offset: int = 0) -> list[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def create(self, entity: AuditLog) -> AuditLog:
        self.db.add(entity)
        self._commit()
        self._refresh(entity)
        return entity
    
    def update(self, entity: AuditLog) -> AuditLog:
        self._commit()
        self._refresh(entity)
        return entity
    
    def delete(self, id: uuid.UUID) -> bool:
        log = self.get_by_id(id)
        if log:
            self.db.delete(log)
            self._commit()
            return True
        return False


class JobRepository(BaseRepository, IJobRepository):
    """SQLAlchemy implementation of job repository."""
    
    def get_by_id(self, id: uuid.UUID) -> Optional[Job]:
        return self.db.query(Job).filter(Job.id == id).first()
    
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        query = self.db.query(Job).filter(Job.tenant_id == tenant_id)
        if status:
            query = query.filter(Job.status == status)
        return (
            query.order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def get_pending_jobs(self, limit: int = 10) -> list[Job]:
        return (
            self.db.query(Job)
            .filter(Job.status.in_([JobStatus.PENDING.value, JobStatus.QUEUED.value]))
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(limit)
            .all()
        )
    
    def update_status(
        self,
        job_id: uuid.UUID,
        status: str,
        progress: Optional[int] = None,
    ) -> Job:
        job = self.get_by_id(job_id)
        if job:
            job.status = status
            if progress is not None:
                job.progress_percent = progress
            self._commit()
            self._refresh(job)
        return job
    
    def count_by_status(self, tenant_id: uuid.UUID) -> dict[str, int]:
        from sqlalchemy import func
        
        result = (
            self.db.query(Job.status, func.count(Job.id))
            .filter(Job.tenant_id == tenant_id)
            .group_by(Job.status)
            .all()
        )
        return {status: count for status, count in result}
    
    def list_all(self, limit: int = 100, offset: int = 0) -> list[Job]:
        return (
            self.db.query(Job)
            .order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def create(self, entity: Job) -> Job:
        self.db.add(entity)
        self._commit()
        self._refresh(entity)
        return entity
    
    def update(self, entity: Job) -> Job:
        self._commit()
        self._refresh(entity)
        return entity
    
    def delete(self, id: uuid.UUID) -> bool:
        job = self.get_by_id(id)
        if job:
            self.db.delete(job)
            self._commit()
            return True
        return False


class PolicyRepository(BaseRepository, IPolicyRepository):
    """SQLAlchemy implementation of policy repository."""
    
    def get_by_id(self, id: uuid.UUID) -> Optional[PolicyRule]:
        return self.db.query(PolicyRule).filter(PolicyRule.id == id).first()
    
    def get_by_tenant(
        self,
        tenant_id: uuid.UUID,
        enabled_only: bool = True,
    ) -> list[PolicyRule]:
        query = self.db.query(PolicyRule).filter(PolicyRule.tenant_id == tenant_id)
        if enabled_only:
            query = query.filter(PolicyRule.is_enabled == True)
        return query.order_by(PolicyRule.priority.asc()).all()
    
    def get_enabled(self, tenant_id: uuid.UUID) -> list[PolicyRule]:
        return self.get_by_tenant(tenant_id, enabled_only=True)
    
    def list_all(self, limit: int = 100, offset: int = 0) -> list[PolicyRule]:
        return (
            self.db.query(PolicyRule)
            .offset(offset)
            .limit(limit)
            .all()
        )
    
    def create(self, entity: PolicyRule) -> PolicyRule:
        self.db.add(entity)
        self._commit()
        self._refresh(entity)
        return entity
    
    def update(self, entity: PolicyRule) -> PolicyRule:
        self._commit()
        self._refresh(entity)
        return entity
    
    def delete(self, id: uuid.UUID) -> bool:
        policy = self.get_by_id(id)
        if policy:
            self.db.delete(policy)
            self._commit()
            return True
        return False
