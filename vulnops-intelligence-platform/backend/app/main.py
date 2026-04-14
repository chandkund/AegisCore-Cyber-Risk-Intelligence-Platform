from __future__ import annotations



import logging

import signal

from contextlib import asynccontextmanager



from fastapi import Depends, FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse

from sqlalchemy import text

from sqlalchemy.orm import Session



from app.api.v1.router import api_router

from app.core.config import get_settings

from app.core.logging_config import configure_logging

from app.db.deps import get_db

from app.db.session import reset_engine

from app.exception_handlers import register_exception_handlers

from app.middleware.rate_limit import rate_limit_middleware

from app.middleware.request_id import REQUEST_ID_HEADER, RequestIdMiddleware



logger = logging.getLogger("aegiscore.api")





@asynccontextmanager

async def lifespan(app: FastAPI):

    configure_logging()

    logger.info("Starting up AegisCore API")

    

    # Setup graceful shutdown handlers

    def handle_signal(sig, frame):

        logger.info(f"Received signal {sig}, initiating graceful shutdown")

    

    signal.signal(signal.SIGTERM, handle_signal)

    signal.signal(signal.SIGINT, handle_signal)

    

    yield

    

    logger.info("Shutting down AegisCore API - cleaning up resources")

    reset_engine()

    logger.info("Cleanup complete")





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

        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],

        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],

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



    # Security headers middleware

    @app.middleware("http")

    async def security_headers(request: Request, call_next):

        response = await call_next(request)

        # Content Security Policy

        response.headers["Content-Security-Policy"] = (

            "default-src 'self'; "

            "script-src 'self'; "

            "style-src 'self' 'unsafe-inline'; "

            "img-src 'self' data:; "

            "font-src 'self'; "

            "connect-src 'self'; "

            "frame-ancestors 'none'; "

            "base-uri 'self'; "

            "form-action 'self';"

        )

        # Prevent MIME type sniffing

        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking

        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy but still useful)

        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy

        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy

        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # HSTS (only in production with HTTPS)

        if settings.app_env == "production":

            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response



    register_exception_handlers(app)



    # Global rate limiting middleware

    @app.middleware("http")

    async def rate_limit(request: Request, call_next):

        return await rate_limit_middleware(request, call_next)



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

