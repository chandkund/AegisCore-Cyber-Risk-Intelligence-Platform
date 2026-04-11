from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_plain,
    hash_refresh_token,
    verify_password,
)
from app.models.oltp import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)

    def login(self, email: str, password: str) -> tuple[str, str, int]:
        user = self.users.get_by_email(email)
        if not user or not user.is_active or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        roles = [ur.role.name for ur in user.roles if ur.role is not None]
        settings = get_settings()
        access = create_access_token(subject=user.id, roles=roles)
        plain = generate_refresh_plain()
        th = hash_refresh_token(plain)
        exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.tokens.create(RefreshToken(user_id=user.id, token_hash=th, expires_at=exp))
        self.db.commit()
        expires_in = settings.access_token_expire_minutes * 60
        return access, plain, expires_in

    def refresh(self, refresh_plain: str) -> tuple[str, str, int]:
        th = hash_refresh_token(refresh_plain)
        row = self.tokens.get_valid_by_hash(th)
        if row is None:
            raise ValueError("Invalid refresh token")
        user = self.users.get_by_id(row.user_id)
        if not user or not user.is_active:
            raise ValueError("User inactive")
        self.tokens.revoke(row.id)
        roles = [ur.role.name for ur in user.roles if ur.role is not None]
        settings = get_settings()
        access = create_access_token(subject=user.id, roles=roles)
        plain = generate_refresh_plain()
        new_hash = hash_refresh_token(plain)
        exp = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.tokens.create(RefreshToken(user_id=user.id, token_hash=new_hash, expires_at=exp))
        self.db.commit()
        return access, plain, settings.access_token_expire_minutes * 60

    def logout(self, refresh_plain: str) -> None:
        self.tokens.revoke_by_hash(hash_refresh_token(refresh_plain))
        self.db.commit()
