from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
    request_id: str | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)
