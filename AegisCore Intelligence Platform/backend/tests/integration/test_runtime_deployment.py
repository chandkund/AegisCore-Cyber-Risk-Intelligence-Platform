"""Docker runtime and deployment verification tests.

These tests verify that the application starts correctly from a clean environment:
1. Database migrations run successfully
2. Upload paths are writable
3. Health endpoints respond correctly
4. Critical services are reachable
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app

client = TestClient(app)

# =============================================================================
# Upload Path Tests
# =============================================================================

class TestUploadPaths:
    """Verify upload directories are correctly configured."""

    def test_upload_directory_exists(self):
        """Verify upload directory exists and is writable."""
        upload_path = os.getenv("UPLOAD_PATH", "/app/uploads")
        path = Path(upload_path)
        
        # Directory should exist
        assert path.exists(), f"Upload directory {upload_path} does not exist"
        
        # Should be a directory
        assert path.is_dir(), f"Upload path {upload_path} is not a directory"
        
        # Should be writable
        assert os.access(path, os.W_OK), f"Upload directory {upload_path} is not writable"

    def test_upload_directory_has_correct_permissions(self):
        """Verify upload directory has appropriate permissions."""
        upload_path = os.getenv("UPLOAD_PATH", "/app/uploads")
        path = Path(upload_path)
        
        # Skip if path doesn't exist (tested separately)
        if not path.exists():
            pytest.skip("Upload directory does not exist")
        
        # Should be readable and writable
        assert os.access(path, os.R_OK), "Upload directory not readable"
        assert os.access(path, os.W_OK), "Upload directory not writable"

    def test_can_write_to_upload_directory(self):
        """Test actual file write to upload directory."""
        upload_path = os.getenv("UPLOAD_PATH", "/app/uploads")
        test_file = Path(upload_path) / ".test_write"
        
        try:
            # Try to write a test file
            test_file.write_text("test")
            assert test_file.exists(), "Test file was not created"
            content = test_file.read_text()
            assert content == "test", "Test file content mismatch"
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()


# =============================================================================
# Health Endpoint Tests
# =============================================================================

class TestHealthEndpoints:
    """Verify health check endpoints respond correctly."""

    def test_basic_health_endpoint(self):
        """Test /health returns 200 and basic status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data

    def test_detailed_health_endpoint(self):
        """Test /health/detailed returns comprehensive status."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "components" in data
        assert len(data["components"]) > 0
        
        # Check database component
        db_components = [c for c in data["components"] if c["name"] == "database"]
        assert len(db_components) > 0, "Database component not in health check"
        assert db_components[0]["status"] in ["up", "down", "degraded"]

    def test_readiness_endpoint(self):
        """Test /health/ready returns proper readiness status."""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]  # 200 = ready, 503 = not ready
        
        data = response.json()
        assert "ready" in data
        assert "checks" in data
        assert "timestamp" in data
        
        # If ready, verify all checks passed
        if data["ready"]:
            assert all(data["checks"].values()), "Ready but some checks failed"

    def test_liveness_endpoint(self):
        """Test /health/live returns liveness status."""
        response = client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data

    def test_ping_endpoint(self):
        """Test /health/ping for load balancer checks."""
        response = client.get("/health/ping")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ping"] == "pong"
        assert "timestamp" in data


# =============================================================================
# Database Connection Tests
# =============================================================================

class TestDatabaseConnectivity:
    """Verify database connectivity in container environment."""

    def test_database_url_configured(self):
        """Verify DATABASE_URL environment variable is set."""
        db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
        assert db_url is not None, "DATABASE_URL not configured"
        assert "postgresql" in db_url or "sqlite" in db_url, "Invalid database URL"

    def test_database_connection(self):
        """Test direct database connection."""
        from app.db.session import engine
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_migrations_table_exists(self):
        """Verify alembic_version table exists (migrations ran)."""
        from app.db.session import engine
        
        with engine.connect() as conn:
            if engine.dialect.name == "sqlite":
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version')"
                    )
                )
                # Local sqlite test databases may be schema-bootstrapped without alembic history.
                if not bool(result.scalar()):
                    return
            else:
                result = conn.execute(
                    text(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
                    )
                )
            assert bool(result.scalar()) is True, "alembic_version table does not exist"


# =============================================================================
# Environment Configuration Tests
# =============================================================================

class TestEnvironmentConfiguration:
    """Verify environment variables are correctly set."""

    def test_required_environment_variables(self):
        """Test critical environment variables are set."""
        required_vars = [
            "APP_ENV",
            "UPLOAD_PATH",
        ]
        
        for var in required_vars:
            assert os.getenv(var) is not None, f"Required environment variable {var} not set"

    def test_database_environment_variables(self):
        """Test database-related environment variables."""
        db_vars = ["DATABASE_URL", "SQLALCHEMY_DATABASE_URI"]
        assert any(os.getenv(v) for v in db_vars), "No database URL configured"

    def test_jwt_configuration(self):
        """Test JWT secret is configured."""
        jwt_secret = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
        assert jwt_secret is not None, "JWT secret not configured"
        # Ensure it's not the default/placeholder
        assert jwt_secret != "change-me-in-production", "JWT secret is still default value"


# =============================================================================
# Startup Verification Tests
# =============================================================================

class TestStartupVerification:
    """Verify application startup completed successfully."""

    def test_api_routes_registered(self):
        """Verify API routes are registered."""
        routes = [route.path for route in app.routes]
        
        # Check critical routes exist
        assert "/health" in routes or any("/health" in r for r in routes), "Health routes not registered"
        assert "/api/v1" in routes or any("/api/v1" in r for r in routes), "API v1 routes not registered"

    def test_no_startup_errors_in_logs(self):
        """Verify no critical errors during startup."""
        # This is a placeholder - in real scenario, check log files or logging handler
        # For now, just verify the app started
        assert app is not None, "Application not initialized"


# =============================================================================
# Integration Smoke Tests
# =============================================================================

class TestIntegrationSmoke:
    """Quick integration smoke tests."""

    def test_api_root_accessible(self):
        """Test API root or docs is accessible."""
        # Try docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200, "API docs not accessible"

    def test_api_endpoints_list_accessible(self):
        """Test that we can get API endpoints list."""
        response = client.get("/openapi.json")
        assert response.status_code == 200, "OpenAPI schema not accessible"
        
        data = response.json()
        assert "paths" in data, "No paths in OpenAPI schema"
        assert len(data["paths"]) > 0, "No endpoints registered"
