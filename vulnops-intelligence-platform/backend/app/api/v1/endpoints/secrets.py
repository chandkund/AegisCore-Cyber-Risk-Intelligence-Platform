from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import AdminDep
from app.schemas.secrets import SecretProviderStatus, SecretResolveResponse
from app.services.secrets_service import SecretsService

router = APIRouter(prefix="/secrets", tags=["secrets"])


@router.get("/status", response_model=SecretProviderStatus)
def provider_status(_: AdminDep):
    svc = SecretsService()
    return SecretProviderStatus(**svc.provider_status())


@router.get("/resolve", response_model=SecretResolveResponse)
def resolve_secret(_: AdminDep, name: str = Query(..., min_length=2, max_length=128)):
    row = SecretsService().resolve_secret(name)
    return SecretResolveResponse(name=name, resolved=row.resolved, source=row.source)
