from __future__ import annotations

import os

import pytest

# Required before importing `app` (settings read at import / first use).
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://invalid:invalid@127.0.0.1:65432/vulnops_test_placeholder",
)
os.environ.setdefault("JWT_SECRET_KEY", "pytest-jwt-secret-key-32chars-min!!")


@pytest.fixture(autouse=True)
def _reset_app_singletons():
    from app.core.config import reset_settings_cache
    from app.db.session import reset_engine
    from app.ml.prioritizer import clear_bundle_cache

    reset_settings_cache()
    reset_engine()
    clear_bundle_cache()
    yield
    reset_settings_cache()
    reset_engine()
    clear_bundle_cache()
