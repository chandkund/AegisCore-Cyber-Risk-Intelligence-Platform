from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.oltp import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserOut, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

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

    def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        rows, total = self.repo.list_users(limit=limit, offset=offset)
        return list(rows), total

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.repo.get_by_id(user_id)

    def create(self, data: UserCreate) -> User:
        email = data.email.strip().lower()
        if self.repo.get_by_email(email):
            raise ValueError("Email already registered")
        user = User(
            email=email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name.strip(),
            is_active=data.is_active,
        )
        self.repo.create(user)
        self.db.commit()
        reloaded = self.repo.get_by_id(user.id)
        return reloaded or user

    def update(self, user_id: uuid.UUID, data: UserUpdate) -> User | None:
        user = self.repo.get_by_id(user_id)
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

    def assign_role(self, user_id: uuid.UUID, role_name: str) -> None:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        role = self.repo.get_role_by_name(role_name)
        if not role:
            raise ValueError("Unknown role")
        self.repo.add_role(user_id, role.id)
        self.db.commit()
