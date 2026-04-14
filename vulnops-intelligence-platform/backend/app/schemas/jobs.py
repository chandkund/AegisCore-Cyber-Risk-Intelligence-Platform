from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    job_kind: str = Field(min_length=2, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobOut(BaseModel):
    id: str
    job_kind: str
    status: str
    payload: dict[str, Any] | None
    result: dict[str, Any] | None
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime
