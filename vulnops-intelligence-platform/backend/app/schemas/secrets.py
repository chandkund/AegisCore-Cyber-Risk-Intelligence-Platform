from __future__ import annotations

from pydantic import BaseModel


class SecretProviderStatus(BaseModel):
    provider: str
    configured: bool
    details: dict[str, str]


class SecretResolveResponse(BaseModel):
    name: str
    resolved: bool
    source: str
