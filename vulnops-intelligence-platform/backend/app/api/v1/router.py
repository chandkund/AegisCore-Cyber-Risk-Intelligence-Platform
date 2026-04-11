from __future__ import annotations

from app.api.v1.endpoints import analytics, assets, auth, cve_records, findings, ml, users
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(findings.router)
api_router.include_router(assets.router)
api_router.include_router(cve_records.router)
api_router.include_router(analytics.router)
api_router.include_router(ml.router)
