from __future__ import annotations



import os

import uuid
from pathlib import Path


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

os.environ.setdefault("AEGISCORE_TEST_MODE", "true")





@pytest.fixture(autouse=True)

def _reset_app_singletons():

    from app.core.config import reset_settings_cache

    from app.db.session import reset_engine

    from app.ml.prioritizer import clear_bundle_cache



    reset_settings_cache()

    reset_engine()

    clear_bundle_cache()

    from app.middleware.login_rate_limit import reset_for_tests as reset_login_rate_limit
    from app.middleware.rate_limit import reset_for_tests as reset_global_rate_limit

    reset_login_rate_limit()
    reset_global_rate_limit()




@pytest.fixture(scope="function")
def test_engine() -> Engine:
    db_url = os.environ.get("AEGISCORE_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    sqlite_path: Path | None = None

    if not db_url or "placeholder" in db_url or "sqlite" in db_url.lower():
        sqlite_path = Path(f".pytest_runtime_{uuid.uuid4().hex}.db")
        db_url = f"sqlite:///{sqlite_path.as_posix()}"

    engine_kwargs = {
        "future": True,
        "pool_pre_ping": True,
        "connect_args": {"check_same_thread": False} if "sqlite" in db_url.lower() else {},
    }
    if "sqlite" in db_url.lower():
        engine_kwargs["use_insertmanyvalues"] = False
    engine = create_engine(db_url, **engine_kwargs)

    if "sqlite" in db_url.lower():
        import uuid as uuid_lib
        from sqlalchemy import event
        from sqlalchemy.sql import sqltypes

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

        # SQLAlchemy UUID sentinel processing can receive floats from SQLite
        # during bulk insert pathways; normalize to stable UUIDs for tests.
        _original_python_uuid = sqltypes._python_UUID

        def _safe_python_uuid(value):
            if isinstance(value, (int, float)):
                return uuid_lib.UUID(int=int(value))
            return _original_python_uuid(value)

        sqltypes._python_UUID = _safe_python_uuid

    from app.db.base import Base
    from app.models import oltp as _oltp_models  # noqa: F401

    if "sqlite" in db_url.lower():
        tables_to_create = [t for t in Base.metadata.tables.values() if not getattr(t, "schema", None)]
        Base.metadata.create_all(bind=engine, tables=tables_to_create)
    else:
        Base.metadata.create_all(bind=engine)

    try:
        yield engine
    finally:
        engine.dispose()
        if sqlite_path is not None and sqlite_path.exists():
            sqlite_path.unlink()





@pytest.fixture(scope="function")
def db(test_engine: Engine) -> Session:
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def db_session(db: Session) -> Session:
    """Backward-compatible alias for tests expecting db_session fixture."""
    return db





@pytest.fixture(scope="function")
def _ensure_default_org(db: Session):
    """Ensure a default organization exists for tests that need it."""
    from app.models.oltp import Organization

    default_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    existing = db.get(Organization, default_id)

    if existing is None:
        db.add(Organization(id=default_id, name="Default Organization", code="default", approval_status="approved"))
        db.flush()


@pytest.fixture(scope="function")
def _seed_roles(db: Session):
    """Seed required roles in the database."""
    from sqlalchemy import select
    from app.models.oltp import Role
    from app.core import rbac

    required_roles = [
        (rbac.ROLE_ADMIN, "Company Administrator"),
        (rbac.ROLE_ANALYST, "Security Analyst"),
        (rbac.ROLE_MANAGER, "Manager"),
        (rbac.ROLE_PLATFORM_OWNER, "Platform Owner"),
    ]

    for role_name, description in required_roles:
        existing = db.execute(
            select(Role).where(Role.name == role_name)
        ).scalar_one_or_none()
        if existing is None:
            db.add(Role(name=role_name, description=description))
    db.flush()


@pytest.fixture(scope="function")
def _seed_platform_owner(db: Session, _seed_roles):
    """Seed platform owner user and aegiscore organization for tests.
    
    Note: Most E2E tests now handle their own seeding within the test transaction
    to ensure data visibility. This fixture is kept for compatibility.
    """
    from app.core.security import hash_password
    from app.core import rbac
    from app.models.oltp import BusinessUnit, Organization, Role, User, UserRole
    from sqlalchemy import select

    default_org_id = uuid.UUID("00000000-0000-4000-8000-000000000001")
    aegiscore_org_id = uuid.UUID("a0000000-0000-4000-8000-000000000002")
    engineering_bu_id = uuid.UUID("a5000001-0000-4000-8000-000000000010")

    # Ensure baseline organizations exist for tests that rely on stable IDs.
    default_org = db.execute(
        select(Organization).where(Organization.code == "default")
    ).scalar_one_or_none()
    if default_org is None:
        db.add(
            Organization(
                id=default_org_id,
                name="Default Organization",
                code="default",
                approval_status="approved",
                is_active=True,
            )
        )
    aegiscore_org = db.execute(
        select(Organization).where(Organization.code == "aegiscore")
    ).scalar_one_or_none()
    if aegiscore_org is None:
        db.add(
            Organization(
                id=aegiscore_org_id,
                name="AegisCore Platform",
                code="aegiscore",
                approval_status="approved",
                is_active=True,
            )
        )
    db.flush()

    # Seed fixed business unit expected by integration tests.
    existing_bu = db.execute(
        select(BusinessUnit).where(BusinessUnit.id == engineering_bu_id)
    ).scalar_one_or_none()
    if existing_bu is None:
        db.add(
            BusinessUnit(
                id=engineering_bu_id,
                tenant_id=aegiscore_org_id,
                name="Engineering",
                code="engineering",
            )
        )
    db.flush()

    role_ids: dict[str, uuid.UUID] = {}
    for role_name in (
        rbac.ROLE_ADMIN,
        rbac.ROLE_ANALYST,
        rbac.ROLE_MANAGER,
        rbac.ROLE_PLATFORM_OWNER,
    ):
        role = db.execute(select(Role).where(Role.name == role_name)).scalar_one_or_none()
        if role is not None:
            role_ids[role_name] = role.id

    def _ensure_user(email: str, full_name: str, password: str, role_name: str) -> None:
        from app.models.oltp import User

        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=aegiscore_org_id,
                email=email,
                full_name=full_name,
                hashed_password=hash_password(password),
                is_active=True,
            )
            db.add(user)
            db.flush()

        role_id = role_ids.get(role_name)
        if role_id is None:
            return
        existing_link = db.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role_id)
        ).scalar_one_or_none()
        if existing_link is None:
            db.add(UserRole(user_id=user.id, role_id=role_id))

    _ensure_user("admin@aegiscore.local", "AegisCore Admin", "AegisCore!demo2026", rbac.ROLE_ADMIN)
    _ensure_user(
        "analyst@aegiscore.local",
        "AegisCore Analyst",
        "AegisCore!demo2026",
        rbac.ROLE_ANALYST,
    )
    _ensure_user(
        "manager@aegiscore.local",
        "AegisCore Manager",
        "AegisCore!demo2026",
        rbac.ROLE_MANAGER,
    )
    _ensure_user(
        "platform@aegiscore.local",
        "Platform Owner",
        "platform123",
        rbac.ROLE_PLATFORM_OWNER,
    )

    db.flush()


@pytest.fixture(scope="function")
def api_client(db: Session, _seed_platform_owner) -> TestClient:
    from app.core.config import reset_settings_cache

    from app.db.deps import get_db

    from app.db.session import reset_engine

    from app.main import create_app

    from app.ml.prioritizer import clear_bundle_cache



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
    reset_settings_cache()
    reset_engine()
    clear_bundle_cache()


# =============================================================================
# Enhanced Test Fixtures for E2E and Integration Testing
# =============================================================================


@pytest.fixture(scope="function")
def authenticated_client(api_client: TestClient, db: Session) -> TestClient:
    """Create an authenticated test client with valid JWT token."""
    from app.models.oltp import Role, User, UserRole
    from sqlalchemy import select
    
    # Create test user
    test_email = "test_e2e@aegiscore.local"
    user = db.execute(select(User).where(User.email == test_email)).scalar_one_or_none()
    
    if user is None:
        from app.core.security import hash_password
        from app.core import rbac
        
        # Get aegiscore org
        from app.models.oltp import Organization
        aegiscore_org = db.execute(
            select(Organization).where(Organization.code == "aegiscore")
        ).scalar_one_or_none()
        
        user = User(
            id=uuid.uuid4(),
            tenant_id=aegiscore_org.id if aegiscore_org else uuid.uuid4(),
            email=test_email,
            hashed_password=hash_password("TestPassword123!"),
            full_name="Test User",
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()
        
        # Assign analyst role
        role = db.execute(
            select(Role).where(Role.name == rbac.ROLE_ANALYST)
        ).scalar_one_or_none()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            db.flush()
    
    # Login
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "TestPassword123!"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    
    # Set authorization header
    api_client.headers["Authorization"] = f"Bearer {data['access_token']}"
    api_client.headers["X-CSRF-Token"] = data.get("csrf_token", "")
    
    return api_client


@pytest.fixture(scope="function")
def platform_owner_client(api_client: TestClient, db: Session) -> TestClient:
    """Create an authenticated platform owner test client."""
    from app.models.oltp import User, Role, UserRole, Organization
    from sqlalchemy import select
    from app.core import rbac
    from app.core.security import hash_password
    
    test_email = "test_platform_owner@aegiscore.local"
    
    user = db.execute(select(User).where(User.email == test_email)).scalar_one_or_none()
    
    if user is None:
        aegiscore_org = db.execute(
            select(Organization).where(Organization.code == "aegiscore")
        ).scalar_one_or_none()
        
        user = User(
            id=uuid.uuid4(),
            tenant_id=aegiscore_org.id if aegiscore_org else uuid.uuid4(),
            email=test_email,
            hashed_password=hash_password("PlatformOwner123!"),
            full_name="Test Platform Owner",
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        db.flush()
        
        # Assign platform owner role
        po_role = db.execute(
            select(Role).where(Role.name == rbac.ROLE_PLATFORM_OWNER)
        ).scalar_one_or_none()
        if po_role:
            db.add(UserRole(user_id=user.id, role_id=po_role.id))
            db.flush()
    
    response = api_client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "PlatformOwner123!"}
    )
    assert response.status_code == 200
    data = response.json()
    
    api_client.headers["Authorization"] = f"Bearer {data['access_token']}"
    api_client.headers["X-CSRF-Token"] = data.get("csrf_token", "")
    
    return api_client


@pytest.fixture(scope="function")
def test_asset(db: Session, _seed_platform_owner):
    """Create a test asset for CRUD operations."""
    from app.models.oltp import Asset, Organization, BusinessUnit
    from sqlalchemy import select
    
    org = db.execute(
        select(Organization).where(Organization.code == "aegiscore")
    ).scalar_one_or_none()
    
    bu = db.execute(
        select(BusinessUnit).where(BusinessUnit.code == "engineering")
    ).scalar_one_or_none()
    
    asset = Asset(
        id=uuid.uuid4(),
        tenant_id=org.id if org else uuid.uuid4(),
        business_unit_id=bu.id if bu else None,
        name="Test Asset E2E",
        asset_type="server",
        ip_address="192.168.1.100",
        is_active=True,
    )
    db.add(asset)
    db.flush()
    
    return asset


@pytest.fixture(scope="function")
def test_user_with_tenant(db: Session, _seed_platform_owner):
    """Create a test user with a dedicated tenant organization."""
    from app.models.oltp import User, Organization, Role, UserRole
    from app.core.security import hash_password
    from app.core import rbac
    from sqlalchemy import select
    
    # Create tenant org
    tenant_org = Organization(
        id=uuid.uuid4(),
        name="Test Tenant E2E",
        code=f"test-tenant-{uuid.uuid4().hex[:8]}",
        approval_status="approved",
        is_active=True,
    )
    db.add(tenant_org)
    db.flush()
    
    # Create user
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_org.id,
        email=f"test_tenant_user_{uuid.uuid4().hex[:8]}@aegiscore.local",
        hashed_password=hash_password("TenantUser123!"),
        full_name="Test Tenant User",
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    db.flush()
    
    # Assign admin role
    admin_role = db.execute(
        select(Role).where(Role.name == rbac.ROLE_ADMIN)
    ).scalar_one_or_none()
    if admin_role:
        db.add(UserRole(user_id=user.id, role_id=admin_role.id))
        db.flush()
    
    return user, tenant_org


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def async_client(test_engine: Engine):
    """Create async test client for async endpoint testing."""
    import asyncio
    from httpx import AsyncClient
    from app.main import create_app
    from app.core.config import get_settings
    
    settings = get_settings()
    app = create_app()
    
    async def _get_client():
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    
    return asyncio.run(_get_client().__anext__())


# =============================================================================
# Test Data Factories
# =============================================================================


class UserFactory:
    """Factory for creating test users."""
    
    def __init__(self, db: Session):
        self.db = db
        self._counter = 0
    
    def create(
        self,
        email: str | None = None,
        full_name: str = "Test User",
        password: str = "TestPassword123!",
        role: str = "analyst",
        tenant_id: uuid.UUID | None = None,
    ):
        from app.models.oltp import User, Role, UserRole, Organization
        from app.core.security import hash_password
        from sqlalchemy import select
        
        self._counter += 1
        
        if email is None:
            email = f"factory_user_{self._counter}_{uuid.uuid4().hex[:6]}@aegiscore.local"
        
        if tenant_id is None:
            org = self.db.execute(
                select(Organization).where(Organization.code == "aegiscore")
            ).scalar_one_or_none()
            tenant_id = org.id if org else uuid.uuid4()
        
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            is_active=True,
            email_verified=True,
        )
        self.db.add(user)
        self.db.flush()
        
        # Assign role
        role_obj = self.db.execute(
            select(Role).where(Role.name == role)
        ).scalar_one_or_none()
        if role_obj:
            self.db.add(UserRole(user_id=user.id, role_id=role_obj.id))
            self.db.flush()
        
        return user


@pytest.fixture(scope="function")
def user_factory(db: Session):
    """Provide UserFactory for creating test users."""
    return UserFactory(db)


class AssetFactory:
    """Factory for creating test assets."""
    
    def __init__(self, db: Session):
        self.db = db
        self._counter = 0
    
    def create(
        self,
        name: str | None = None,
        asset_type: str = "server",
        tenant_id: uuid.UUID | None = None,
    ):
        from app.models.oltp import Asset, Organization, BusinessUnit
        from sqlalchemy import select
        
        self._counter += 1
        
        if name is None:
            name = f"Factory Asset {self._counter}"
        
        if tenant_id is None:
            org = self.db.execute(
                select(Organization).where(Organization.code == "aegiscore")
            ).scalar_one_or_none()
            tenant_id = org.id if org else uuid.uuid4()
        
        bu = self.db.execute(
            select(BusinessUnit).where(BusinessUnit.code == "engineering")
        ).scalar_one_or_none()
        
        asset = Asset(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            business_unit_id=bu.id if bu else None,
            name=name,
            asset_type=asset_type,
            ip_address=f"192.168.{self._counter // 256}.{self._counter % 256}",
            is_active=True,
        )
        self.db.add(asset)
        self.db.flush()
        
        return asset


@pytest.fixture(scope="function")
def asset_factory(db: Session):
    """Provide AssetFactory for creating test assets."""
    return AssetFactory(db)


# =============================================================================
# Security Testing Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def csrf_token(api_client: TestClient):
    """Get CSRF token from health or auth endpoint."""
    response = api_client.get("/health")
    # CSRF token is set via middleware
    return api_client.cookies.get("csrf_token", "")


@pytest.fixture(scope="function")
def rate_limit_test_client(db: Session, _seed_platform_owner):
    """Create a client for rate limit testing with isolated rate limit state."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.db.deps import get_db
    
    # Reset rate limits before test
    from app.middleware.rate_limit import reset_for_tests
    from app.middleware.login_rate_limit import reset_for_tests as reset_login_limit
    reset_for_tests()
    reset_login_limit()
    
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


# =============================================================================
# Performance Testing Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def benchmark_config():
    """Configuration for performance benchmarks."""
    return {
        "warmup_runs": 5,
        "benchmark_runs": 100,
        "max_latency_ms": 200,  # 200ms p95 requirement
        "max_p99_latency_ms": 500,  # 500ms p99 requirement
    }


# =============================================================================
# Cleanup Fixtures
# =============================================================================


@pytest.fixture(scope="function", autouse=True)
def cleanup_after_test(db: Session):
    """Clean up test data after each test."""
    yield
    # Additional cleanup if needed beyond transaction rollback
    pass

