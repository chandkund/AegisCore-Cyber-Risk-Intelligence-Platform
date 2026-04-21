from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core import rbac
from app.core.security import hash_password
from app.models.oltp import OrganizationInvitation, User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.core.security import generate_refresh_plain, hash_refresh_token


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
        self.invites = InvitationRepository(db)

    def to_out(self, user: User) -> UserOut:
        roles = [ur.role.name for ur in user.roles if ur.role is not None]
        return UserOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            roles=roles,
        )

    def list_users(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[User], int]:
        rows, total = self.repo.list_users_by_tenant(
            tenant_id=tenant_id, limit=limit, offset=offset
        )
        return list(rows), total

    def get(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> User | None:
        user = self.repo.get_by_id(user_id)
        if not user or user.tenant_id != tenant_id:
            return None
        return user

    def create(self, data: UserCreate, *, tenant_id: uuid.UUID) -> User:
        email = data.email.strip().lower()
        if self.repo.get_by_email(email):
            raise ValueError("Email already registered")
        user = User(
            tenant_id=tenant_id,
            email=email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=data.is_active,
        )
        self.repo.create(user)
        self.db.commit()
        reloaded = self.get(user.id, tenant_id)
        return reloaded or user

    def update(self, user_id: uuid.UUID, data: UserUpdate, *, tenant_id: uuid.UUID) -> User | None:
        user = self.get(user_id, tenant_id)
        if not user:
            return None
        if data.full_name is not None:
            user.full_name = data.full_name.strip()
        if data.is_active is not None:
            user.is_active = data.is_active
        if data.password is not None:
            user.hashed_password = hash_password(data.password)
        self.db.commit()
        self.db.refresh(user)
        return user

    def assign_role(self, user_id: uuid.UUID, role_name: str, *, tenant_id: uuid.UUID) -> None:
        user = self.get(user_id, tenant_id)
        if not user:
            raise ValueError("User not found")
        if role_name == rbac.ROLE_PLATFORM_OWNER:
            raise ValueError("Role cannot be assigned in tenant context")
        role = self.repo.get_role_by_name(role_name)
        if not role:
            raise ValueError("Unknown role")
        self.repo.add_role(user_id, role.id)
        self.db.commit()

    async def create_and_send_invitation(
        self,
        *,
        tenant_id: uuid.UUID,
        inviter_user_id: uuid.UUID,
        inviter_name: str,
        company_name: str,
        email: str,
        role_name: str,
        expires_in_hours: int = 72,
        accept_url: str = "http://localhost:3000/accept-invitation",
    ) -> tuple[OrganizationInvitation, str]:
        """Create invitation and send email notification."""
        from app.services.email_service import get_email_service

        # Create the invitation
        invite, plain_token = self.create_invitation(
            tenant_id=tenant_id,
            inviter_user_id=inviter_user_id,
            email=email,
            role_name=role_name,
            expires_in_hours=expires_in_hours,
        )

        # Send invitation email
        email_service = get_email_service()
        await email_service.send_invitation_email(
            to_email=email,
            inviter_name=inviter_name,
            company_name=company_name,
            invitation_token=plain_token,
            accept_url=accept_url,
            expires_in_hours=expires_in_hours,
        )

        return invite, plain_token

    def create_invitation(
        self,
        *,
        tenant_id: uuid.UUID,
        inviter_user_id: uuid.UUID,
        email: str,
        role_name: str,
        expires_in_hours: int,
    ) -> tuple[OrganizationInvitation, str]:
        normalized_email = email.strip().lower()
        if role_name == rbac.ROLE_PLATFORM_OWNER:
            raise ValueError("Role cannot be assigned in tenant context")
        if role_name not in rbac.ALL_ROLES:
            raise ValueError("Unknown role")
        if self.repo.get_by_email(normalized_email, tenant_id=tenant_id):
            raise ValueError("User already exists for this company")
        if self.invites.find_active_by_email(tenant_id, normalized_email):
            raise ValueError("An active invitation already exists for this email")
        plain = generate_refresh_plain()
        invite = self.invites.create(
            OrganizationInvitation(
                tenant_id=tenant_id,
                invited_by_user_id=inviter_user_id,
                email=normalized_email,
                role_name=role_name,
                token_hash=hash_refresh_token(plain),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
            )
        )
        self.db.commit()
        return invite, plain
