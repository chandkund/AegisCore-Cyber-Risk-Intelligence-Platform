from __future__ import annotations

from app.api.v1.endpoints import (
    analytics,
    assistant,
    assets,
    attack_path,
    auth,
    cve_records,
    explanations,
    findings,
    ingestion,
    jobs,
    ml,
    policy,
    prioritization,
    search,
    secrets,
    simulation,
    tickets,
    uploads,
    users,
)
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(findings.router)
api_router.include_router(assets.router)
api_router.include_router(cve_records.router)
api_router.include_router(ingestion.router)
api_router.include_router(analytics.router)
api_router.include_router(policy.router)
api_router.include_router(jobs.router)
api_router.include_router(secrets.router)
api_router.include_router(ml.router)
api_router.include_router(prioritization.router)
api_router.include_router(explanations.router)
api_router.include_router(search.router)
api_router.include_router(simulation.router)
api_router.include_router(attack_path.router)
api_router.include_router(assistant.router)
api_router.include_router(tickets.router)
api_router.include_router(uploads.router)
