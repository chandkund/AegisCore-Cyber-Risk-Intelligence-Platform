from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.oltp import Role, User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(func.lower(User.email) == normalized)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(User.id == user_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_users(self, *, limit: int, offset: int) -> tuple[Sequence[User], int]:
        total = self.db.scalar(select(func.count()).select_from(User)) or 0
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = self.db.execute(stmt).unique().scalars().all()
        return rows, int(total)

    def list_users_by_tenant(
        self, *, tenant_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[Sequence[User], int]:
        total = (
            self.db.scalar(
                select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
            )
            or 0
        )
        stmt = (
            select(User)
            .options(joinedload(User.roles).joinedload(UserRole.role))
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = self.db.execute(stmt).unique().scalars().all()
        return rows, int(total)

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def get_role_by_name(self, name: str) -> Role | None:
        return self.db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()

    def add_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        self.db.merge(UserRole(user_id=user_id, role_id=role_id))
        self.db.flush()
