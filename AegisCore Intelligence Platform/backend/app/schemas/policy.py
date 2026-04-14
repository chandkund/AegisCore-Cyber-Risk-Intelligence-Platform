from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyRuleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    conditions: dict[str, Any]
    action: str = Field(default="flag", max_length=64)
    severity: str = Field(default="MEDIUM", max_length=16)
    is_enabled: bool = True


class PolicyRuleOut(BaseModel):
    id: str
    name: str
    description: str | None
    conditions: dict[str, Any]
    action: str
    severity: str
    is_enabled: bool
    created_at: datetime


class PolicyViolation(BaseModel):
    policy_rule_id: str
    policy_name: str
    finding_id: str
    action: str
    severity: str
    reason: str
