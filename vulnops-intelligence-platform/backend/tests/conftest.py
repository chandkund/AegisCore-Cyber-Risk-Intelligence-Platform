from __future__ import annotations



import os

import uuid



import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine

from sqlalchemy.engine import Engine

from sqlalchemy.orm import Session, sessionmaker



# Required before importing `app` (settings read at import / first use).

os.environ.setdefault(

    "DATABASE_URL",

    "postgresql+psycopg://invalid:invalid@127.0.0.1:65432/aegiscore_test_placeholder",

)

os.environ.setdefault("JWT_SECRET_KEY", "pytest-jwt-secret-key-32chars-min!!")

os.environ.setdefault("ML_INFERENCE_ENABLED", "false")





@pytest.fixture(autouse=True)

def _reset_app_singletons():

    from app.core.config import reset_settings_cache

    from app.db.session import reset_engine

    from app.ml.prioritizer import clear_bundle_cache



    reset_settings_cache()

    reset_engine()

    clear_bundle_cache()





@pytest.fixture(scope="session")

def test_engine() -> Engine:

    db_url = os.environ.get("AEGISCORE_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")

    if not db_url or "placeholder" in db_url:

        pytest.skip("Set AEGISCORE_TEST_DATABASE_URL to run database-backed tests")

    engine = create_engine(db_url, future=True, pool_pre_ping=True)

    yield engine

    engine.dispose()





@pytest.fixture(scope="function")

def db(test_engine: Engine) -> Session:

    from app.db.base import Base



    Base.metadata.create_all(bind=test_engine)

    connection = test_engine.connect()

    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)

    session = SessionLocal()

    try:

        yield session

    finally:

        session.close()

        transaction.rollback()

        connection.close()





@pytest.fixture(autouse=True)

def _ensure_default_org(db: Session):

    from app.models.oltp import Organization



    default_id = uuid.UUID("00000000-0000-4000-8000-000000000001")

    existing = db.get(Organization, default_id)

    if existing is None:

        db.add(Organization(id=default_id, name="Default Organization", code="default"))

        db.flush()





@pytest.fixture(scope="function")

def api_client(db: Session) -> TestClient:

    from app.db.deps import get_db

    from app.main import create_app



    app = create_app()



    def _override_get_db():

        try:

            yield db

        finally:

            pass



    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app) as client:

        yield client

    app.dependency_overrides.clear()

    yield

    reset_settings_cache()

    reset_engine()

    clear_bundle_cache()

