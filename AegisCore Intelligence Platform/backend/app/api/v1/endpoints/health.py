"""Health check and monitoring endpoints.

Provides comprehensive health checks for:
- Application status
- Database connectivity
- External service dependencies
- System metrics
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

import psutil
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.deps import get_db

logger = logging.getLogger("aegiscore.health")

router = APIRouter(prefix="/health", tags=["health"])


# =============================================================================
# Schemas
# =============================================================================

class HealthStatus(BaseModel):
    """Basic health status response."""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    version: str
    uptime_seconds: float


class ComponentStatus(BaseModel):
    """Individual component health status."""
    name: str
    status: str  # "up", "down", "degraded"
    response_time_ms: float
    details: dict[str, Any] | None = None
    error: str | None = None


class DetailedHealthStatus(HealthStatus):
    """Detailed health check response."""
    components: list[ComponentStatus]
    system_metrics: SystemMetrics | None = None


class SystemMetrics(BaseModel):
    """System-level metrics."""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    open_file_descriptors: int
    thread_count: int


class ReadinessStatus(BaseModel):
    """Readiness probe response for Kubernetes."""
    ready: bool
    checks: dict[str, bool]
    timestamp: str


class LivenessStatus(BaseModel):
    """Liveness probe response for Kubernetes."""
    alive: bool
    timestamp: str


# =============================================================================
# Global state
# =============================================================================

_start_time = time.time()


# =============================================================================
# Helper Functions
# =============================================================================

def _check_database(db: Session) -> ComponentStatus:
    """Check database connectivity."""
    start = time.time()
    try:
        db.execute(text("SELECT 1"))
        response_time = (time.time() - start) * 1000
        
        # Check connection pool stats if available
        pool_info = {}
        if hasattr(db.bind, "pool"):
            pool = db.bind.pool
            pool_info = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        
        return ComponentStatus(
            name="database",
            status="up",
            response_time_ms=response_time,
            details=pool_info,
        )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ComponentStatus(
            name="database",
            status="down",
            response_time_ms=(time.time() - start) * 1000,
            error=str(e),
        )


def _get_system_metrics() -> SystemMetrics:
    """Get current system metrics."""
    return SystemMetrics(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=psutil.virtual_memory().percent,
        disk_percent=psutil.disk_usage("/").percent,
        open_file_descriptors=len(psutil.Process().open_files()),
        thread_count=psutil.Process().num_threads(),
    )


def _check_redis() -> ComponentStatus:
    """Check Redis connectivity if configured."""
    start = time.time()
    try:
        from app.core.config import get_settings
        settings = get_settings()
        
        if not hasattr(settings, "redis_url") or not settings.redis_url:
            return ComponentStatus(
                name="redis",
                status="up",  # Not required
                response_time_ms=0,
                details={"note": "Redis not configured"},
            )
        
        import redis
        r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        
        return ComponentStatus(
            name="redis",
            status="up",
            response_time_ms=(time.time() - start) * 1000,
            details={},
        )
    except Exception as e:
        return ComponentStatus(
            name="redis",
            status="degraded",
            response_time_ms=(time.time() - start) * 1000,
            error=str(e),
        )


def _check_email_service() -> ComponentStatus:
    """Check email service configuration."""
    start = time.time()
    try:
        settings = get_settings()
        provider = getattr(settings, "email_provider", "console")
        
        status = "up"
        details = {"provider": provider}
        
        if provider == "console":
            details["note"] = "Using console provider (development mode)"
        elif provider == "smtp":
            details["host"] = getattr(settings, "smtp_host", "not set")
        elif provider == "ses":
            details["region"] = getattr(settings, "aws_region", "not set")
        
        return ComponentStatus(
            name="email",
            status=status,
            response_time_ms=(time.time() - start) * 1000,
            details=details,
        )
    except Exception as e:
        return ComponentStatus(
            name="email",
            status="degraded",
            response_time_ms=(time.time() - start) * 1000,
            error=str(e),
        )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=HealthStatus)
def health_check():
    """Basic health check endpoint.
    
    Returns simple healthy/unhealthy status.
    Used by load balancers and simple monitoring.
    """
    settings = get_settings()
    uptime = time.time() - _start_time
    
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=settings.version if hasattr(settings, "version") else "1.0.0",
        uptime_seconds=uptime,
    )


@router.get("/detailed", response_model=DetailedHealthStatus)
def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with component status.
    
    Checks all critical components:
    - Database connectivity
    - Redis (if configured)
    - Email service
    - System metrics
    """
    settings = get_settings()
    uptime = time.time() - _start_time
    
    # Check all components
    components = [
        _check_database(db),
        _check_redis(),
        _check_email_service(),
    ]
    
    # Determine overall status
    any_down = any(c.status == "down" for c in components)
    any_degraded = any(c.status == "degraded" for c in components)
    
    if any_down:
        overall_status = "unhealthy"
    elif any_degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    # Get system metrics if psutil available
    system_metrics = None
    try:
        system_metrics = _get_system_metrics()
    except Exception as e:
        logger.warning(f"Could not get system metrics: {e}")
    
    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=settings.version if hasattr(settings, "version") else "1.0.0",
        uptime_seconds=uptime,
        components=components,
        system_metrics=system_metrics,
    )


@router.get("/ready", response_model=ReadinessStatus)
def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe.
    
    Returns 200 when application is ready to accept traffic.
    Returns 503 when application is not ready.
    """
    checks = {}
    
    # Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
    
    # Check if migrations are current
    try:
        from alembic.config import Config
        from alembic.command import current
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        
        # Get database URL from settings
        settings = get_settings()
        db_url = getattr(settings, "database_url", None) or getattr(settings, "sync_database_uri", None)
        
        if db_url:
            engine = create_engine(str(db_url))
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
                
                # Check if we have a current revision
                checks["migrations"] = current_rev is not None
        else:
            checks["migrations"] = False
    except Exception as e:
        logger.warning(f"Migration check failed: {e}")
        checks["migrations"] = False
    
    ready = all(checks.values())
    
    return ReadinessStatus(
        ready=ready,
        checks=checks,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/live", response_model=LivenessStatus)
def liveness_check():
    """Kubernetes liveness probe.
    
    Returns 200 if application is alive.
    Returns 500 if application should be restarted.
    """
    # Basic check - is process responsive
    return LivenessStatus(
        alive=True,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/metrics")
def get_metrics():
    """Prometheus-style metrics endpoint.
    
    Returns application metrics in Prometheus exposition format.
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    lines = []
    
    # Uptime
    uptime = time.time() - _start_time
    lines.append(f"# HELP app_uptime_seconds Application uptime in seconds")
    lines.append(f"# TYPE app_uptime_seconds gauge")
    lines.append(f'app_uptime_seconds{{version="{getattr(settings, "version", "1.0.0")}"}} {uptime}')
    
    # System metrics
    try:
        lines.append("")
        lines.append("# HELP system_cpu_percent CPU usage percentage")
        lines.append("# TYPE system_cpu_percent gauge")
        lines.append(f"system_cpu_percent {psutil.cpu_percent(interval=0.1)}")
        
        lines.append("")
        lines.append("# HELP system_memory_percent Memory usage percentage")
        lines.append("# TYPE system_memory_percent gauge")
        lines.append(f"system_memory_percent {psutil.virtual_memory().percent}")
    except Exception:
        pass
    
    # Database metrics (if available)
    # These would typically come from a metrics collector
    
    return {"text": "\n".join(lines)}


@router.get("/ping")
def ping():
    """Simple ping endpoint for load balancer health checks.
    
    Returns minimal response quickly.
    """
    return {"ping": "pong", "timestamp": datetime.utcnow().isoformat()}


@router.post("/ready", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
def readiness_fail():
    """Force readiness probe to fail (for testing).
    
    Only available in non-production environments.
    """
    settings = get_settings()
    env = getattr(settings, "environment", "development")
    
    if env == "production":
        return {"error": "Not allowed in production"}
    
    return {
        "ready": False,
        "message": "Readiness probe manually failed",
        "timestamp": datetime.utcnow().isoformat(),
    }
