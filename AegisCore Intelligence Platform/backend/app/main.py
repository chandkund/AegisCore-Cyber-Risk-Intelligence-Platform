from __future__ import annotations



import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import signal

from contextlib import asynccontextmanager



from fastapi import Depends, FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse, RedirectResponse

from sqlalchemy import text

from sqlalchemy.orm import Session



from app.api.v1.router import api_router

from app.core.config import get_settings

from app.core.logging_config import configure_logging

from app.db.deps import get_db

from app.db.base import Base
from app.db.session import reset_engine

from app.exception_handlers import register_exception_handlers

from app.middleware.csrf_protection import CSRFProtectionMiddleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware



logger = logging.getLogger("aegiscore.api")





@asynccontextmanager

async def lifespan(app: FastAPI):

    configure_logging()

    logger.info("Starting up AegisCore API")
    _ensure_schema_for_local_dev()

    # Seed initial data (roles and platform owner)
    _seed_initial_data()

    

    # Setup graceful shutdown handlers (Unix-only, skip in tests/threaded contexts)

    def handle_signal(sig, frame):

        logger.info(f"Received signal {sig}, initiating graceful shutdown")

    

    try:

        # SIGTERM is not available on Windows

        if hasattr(signal, 'SIGTERM'):

            signal.signal(signal.SIGTERM, handle_signal)

        signal.signal(signal.SIGINT, handle_signal)

    except ValueError:

        # Signal handling only works in main thread (tests run in separate threads)

        pass

    

    yield

    

    logger.info("Shutting down AegisCore API - cleaning up resources")

    reset_engine()

    logger.info("Cleanup complete")



def _seed_initial_data():
    """Seed initial roles and platform owner if they don't exist."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        # Tests seed explicit fixtures and override DB dependencies.
        return
    import uuid
    from sqlalchemy import select, inspect
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import ProgrammingError
    from app.db.session import get_engine
    from app.core.security import hash_password
    from app.core import rbac

    engine = get_engine()
    
    # Check if tables exist first
    try:
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if "roles" not in tables or "organizations" not in tables:
                logger.warning("Database tables not initialized. Run migrations: alembic upgrade head")
                return
    except Exception as e:
        logger.warning(f"Cannot check database tables: {e}")
        return
    
    with Session(engine) as db:
        try:
            from app.models.oltp import Organization, Role, User, UserRole
            from app.repositories.user_repository import UserRepository
            
            # Seed roles
            required_roles = [
                (rbac.ROLE_ADMIN, "Company Administrator"),
                (rbac.ROLE_ANALYST, "Security Analyst"),
                (rbac.ROLE_MANAGER, "Manager"),
                (rbac.ROLE_PLATFORM_OWNER, "Platform Owner"),
            ]
            for role_name, description in required_roles:
                existing = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
                if existing is None:
                    db.add(Role(name=role_name, description=description))
            db.commit()

            # Seed platform owner organization
            aegiscore_id = uuid.UUID("00000000-0000-4000-8000-000000000002")
            aegiscore_org = db.get(Organization, aegiscore_id)
            if aegiscore_org is None:
                aegiscore_org = Organization(
                    id=aegiscore_id,
                    name="AegisCore Platform",
                    code="aegiscore",
                    approval_status="approved",
                    is_active=True,
                )
                db.add(aegiscore_org)
                db.commit()
                logger.info("Created AegisCore platform organization")

            # Seed platform owner user with secure random password
            platform_owner = UserRepository(db).get_by_email("platform@aegiscore.local", tenant_id=aegiscore_id)
            if platform_owner is None:
                import secrets
                import string
                # Generate a secure 32-character random password
                secure_password = ''.join(secrets.choice(
                    string.ascii_letters + string.digits + string.punctuation
                ) for _ in range(32))
                
                platform_owner = User(
                    id=uuid.uuid4(),
                    tenant_id=aegiscore_id,
                    email="platform@aegiscore.local",
                    hashed_password=hash_password(secure_password),
                    full_name="Platform Owner",
                    is_active=True,
                    email_verified=True,
                    require_password_change=True,  # Force password change on first login
                )
                db.add(platform_owner)
                db.flush()
                # Assign platform_owner role
                po_role = UserRepository(db).get_role_by_name(rbac.ROLE_PLATFORM_OWNER)
                if po_role:
                    db.add(UserRole(user_id=platform_owner.id, role_id=po_role.id))
                db.commit()
                
                # Log the password with clear warning - this is the ONLY time it's shown
                logger.warning("=" * 80)
                logger.warning("PLATFORM OWNER ACCOUNT CREATED")
                logger.warning("=" * 80)
                logger.warning("Email: platform@aegiscore.local")
                logger.warning(f"Password: {secure_password}")
                logger.warning("IMPORTANT: Save this password immediately! It will not be shown again.")
                logger.warning("You can change this password after first login.")
                logger.warning("=" * 80)
        except ProgrammingError as e:
            logger.warning(f"Database schema not ready, skipping seed: {e}")


def _ensure_schema_for_local_dev() -> None:
    """Create baseline schema automatically for local/test sqlite runs."""
    settings = get_settings()
    if settings.app_env in {"production", "staging"}:
        return
    if not settings.database_url_sync.startswith("sqlite"):
        return
    try:
        from app import models  # noqa: F401
        from app.db.session import get_engine

        engine = get_engine()
        local_tables = [table for table in Base.metadata.tables.values() if not table.schema]
        Base.metadata.create_all(engine, tables=local_tables)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Local schema bootstrap skipped: %s", exc)





def create_app() -> FastAPI:

    settings = get_settings()
    os.environ.setdefault("APP_ENV", settings.app_env)
    upload_path = os.environ.setdefault("UPLOAD_PATH", os.environ.get("UPLOAD_DIR", "/app/uploads"))
    Path(upload_path).mkdir(parents=True, exist_ok=True)

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
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-CSRF-Token"],
    )



    # Body size limit middleware (10MB)

    @app.middleware("http")

    async def body_size_limit(request: Request, call_next):

        max_size = 10 * 1024 * 1024  # 10MB

        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > max_size:

            return JSONResponse(

                status_code=413,

                content={"detail": "Request body too large", "code": "content_too_large"},

            )

        return await call_next(request)



    # Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=31536000,  # 1 year
        hsts_include_subdomains=True,
        hsts_preload=True,
        enable_csp=True,
    )

    # CSRF protection middleware (double-submit cookie pattern)
    # Exempts: docs, health, login, register (no session yet)
    app.add_middleware(
        CSRFProtectionMiddleware,
        secret_key=settings.jwt_secret_key,
        cookie_name="csrf_token",
        header_name="X-CSRF-Token",
        cookie_max_age=3600,  # 1 hour
        token_max_age=60,  # 1 minute for validation
    )

    register_exception_handlers(app)



    # Global rate limiting middleware

    @app.middleware("http")

    async def rate_limit(request: Request, call_next):

        return await rate_limit_middleware(request, call_next)



    @app.get("/health", tags=["health"])

    def liveness():
        now = datetime.now(timezone.utc).isoformat()
        return {"status": "healthy", "timestamp": now, "version": "1.0.0", "uptime_seconds": 0}



    @app.get("/ready", tags=["health"])

    def readiness(db: Session = Depends(get_db)):

        db.execute(text("SELECT 1"))

        return {"status": "ready"}

    @app.get("/health/detailed", tags=["health"])
    def health_detailed(db: Session = Depends(get_db)):
        db_ok = True
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        now = datetime.now(timezone.utc).isoformat()
        return {
            "status": "healthy" if db_ok else "degraded",
            "timestamp": now,
            "components": [{"name": "database", "status": "up" if db_ok else "down"}],
        }

    @app.get("/health/ready", tags=["health"])
    def health_ready(db: Session = Depends(get_db)):
        now = datetime.now(timezone.utc).isoformat()
        try:
            db.execute(text("SELECT 1"))
            return {"ready": True, "checks": {"database": True}, "timestamp": now}
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"ready": False, "checks": {"database": False}, "timestamp": now},
            )

    @app.get("/health/live", tags=["health"])
    def health_live():
        return {"alive": True, "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/health/ping", tags=["health"])
    def health_ping():
        return {"ping": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/docs", include_in_schema=False)
    def docs_alias():
        return RedirectResponse(url=f"{settings.api_v1_prefix}/docs")

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_alias():
        return RedirectResponse(url=f"{settings.api_v1_prefix}/openapi.json")



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



    if settings.otel_enabled:

        try:

            from opentelemetry import trace

            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            from opentelemetry.sdk.resources import Resource

            from opentelemetry.sdk.trace import TracerProvider

            from opentelemetry.sdk.trace.export import BatchSpanProcessor



            provider = TracerProvider(

                resource=Resource.create({"service.name": settings.otel_service_name})

            )

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)

            provider.add_span_processor(BatchSpanProcessor(exporter))

            trace.set_tracer_provider(provider)

            FastAPIInstrumentor.instrument_app(app)

            logger.info("OpenTelemetry instrumentation enabled")

        except Exception as e:  # noqa: BLE001

            logger.warning("OpenTelemetry instrumentation unavailable: %s", e)



    return app





app = create_app()

