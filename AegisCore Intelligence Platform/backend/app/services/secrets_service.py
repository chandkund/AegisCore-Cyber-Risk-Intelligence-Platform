from __future__ import annotations

import os
from dataclasses import dataclass

from app.core.config import get_settings


@dataclass
class SecretLookup:
    resolved: bool
    source: str
    value: str | None = None


class SecretsService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def provider_status(self) -> dict:
        provider = self.settings.secret_provider.lower()
        configured = False
        details = {}
        if provider == "env":
            configured = True
            details = {"mode": "environment-only"}
        elif provider == "vault":
            configured = bool(self.settings.vault_addr)
            details = {"vault_addr": self.settings.vault_addr or ""}
        else:
            configured = bool(self.settings.secret_provider_prefix)
            details = {"prefix": self.settings.secret_provider_prefix}
        return {"provider": provider, "configured": configured, "details": details}

    def resolve_secret(self, name: str) -> SecretLookup:
        provider = self.settings.secret_provider.lower()
        if provider == "env":
            value = os.environ.get(name)
            return SecretLookup(resolved=value is not None, source="env", value=value)
        # Provider integration shim: supports namespaced env mirror for vault/aws/gcp/azure.
        namespaced = f"{self.settings.secret_provider_prefix}{name}"
        value = os.environ.get(namespaced) or os.environ.get(name)
        return SecretLookup(
            resolved=value is not None,
            source=f"{provider}-shim",
            value=value,
        )
