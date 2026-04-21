from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    full_name: str = Field(min_length=1, max_length=200)
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=256)


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    roles: list[str] = []


class UserRoleAssign(BaseModel):
    role_name: str = Field(min_length=1, max_length=64)


class UserInvitationCreate(BaseModel):
    email: EmailStr
    role_name: str = Field(min_length=1, max_length=64)
    expires_in_hours: int = Field(default=72, ge=1, le=168)


class UserInvitationOut(BaseModel):
    invitation_token: str
    email: EmailStr
    role_name: str
    expires_at: datetime
