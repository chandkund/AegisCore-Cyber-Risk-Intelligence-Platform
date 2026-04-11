from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.deps import get_db
from app.db.session import reset_engine
from app.exception_handlers import register_exception_handlers
from app.middleware.request_id import REQUEST_ID_HEADER, RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield
    reset_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.project_name,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", REQUEST_ID_HEADER],
    )
    register_exception_handlers(app)

    @app.get("/health", tags=["health"])
    def liveness():
        return {"status": "ok"}

    @app.get("/ready", tags=["health"])
    def readiness(db: Session = Depends(get_db)):
        db.execute(text("SELECT 1"))
        return {"status": "ready"}

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    if settings.prometheus_metrics_enabled:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
        ).instrument(app).expose(
            app,
            endpoint="/metrics",
            include_in_schema=False,
        )

    return app


app = create_app()
