from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.security import decode_access_token
from app.db.deps import get_db
from app.repositories.user_repository import UserRepository

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    id: uuid.UUID
    email: str
    full_name: str
    roles: frozenset[str]


def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> Principal:
    if cred is None or not cred.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if payload.get("typ") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        uid = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject"
        ) from e

    repo = UserRepository(db)
    user = repo.get_by_id(uid)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )
    role_names = frozenset(ur.role.name for ur in user.roles if ur.role is not None)
    return Principal(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        roles=role_names,
    )


def require_roles(*allowed: str) -> Callable[..., Principal]:
    allowed_set = frozenset(allowed)

    def _dep(principal: Annotated[Principal, Depends(get_current_user)]) -> Principal:
        if rbac.ROLE_ADMIN in principal.roles:
            return principal
        if not (principal.roles & allowed_set):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return principal

    return _dep


AdminDep = Annotated[Principal, Depends(require_roles(rbac.ROLE_ADMIN))]
WriterDep = Annotated[
    Principal,
    Depends(require_roles(rbac.ROLE_ADMIN, rbac.ROLE_ANALYST)),
]
ReaderDep = Annotated[
    Principal,
    Depends(require_roles(rbac.ROLE_ADMIN, rbac.ROLE_ANALYST, rbac.ROLE_MANAGER)),
]
