from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TicketProvider = Literal["github", "jira", "servicenow"]


class TicketCreateRequest(BaseModel):
    provider: TicketProvider
    title: str = Field(min_length=3, max_length=500)
    description: str = Field(min_length=3, max_length=10000)
    assignee: str | None = Field(default=None, max_length=320)
    labels: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketSyncRequest(BaseModel):
    status: str = Field(min_length=2, max_length=32)
    payload: dict[str, Any] | None = None


class TicketOut(BaseModel):
    id: str
    finding_id: str
    provider: TicketProvider
    external_ticket_id: str
    external_url: str | None
    status: str
    title: str
    payload: dict[str, Any] | None
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime
