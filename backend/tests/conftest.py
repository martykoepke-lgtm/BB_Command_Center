"""
Shared test fixtures — async DB, httpx client, auth helpers.

Uses a separate test PostgreSQL database. Set TEST_DATABASE_URL env var
or defaults to bb_command_test on localhost.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.auth import create_access_token, hash_password

# ---------------------------------------------------------------------------
# Test database engine (separate DB to avoid clobbering dev data)
# ---------------------------------------------------------------------------

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/bb_command_test",
)

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Create all tables once per test session, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db():
    """Provide a fresh DB session per test, rolled back after."""
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db: AsyncSession) -> User:
    """Create a standard analyst user for tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"analyst-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("testpass123"),
        full_name="Test Analyst",
        role="analyst",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    """Create an admin user for tests requiring elevated privileges."""
    user = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("adminpass123"),
        full_name="Test Admin",
        role="admin",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def manager_user(db: AsyncSession) -> User:
    """Create a manager user for tests."""
    user = User(
        id=uuid.uuid4(),
        email=f"manager-{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("mgrpass123"),
        full_name="Test Manager",
        role="manager",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _make_client(app, db_session: AsyncSession, user: User | None):
    """Build an httpx AsyncClient with dependency overrides."""

    async def _override_db():
        yield db_session

    async def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    if user:
        app.dependency_overrides[get_current_user] = _override_user

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest_asyncio.fixture
async def client(db: AsyncSession, test_user: User):
    """Authenticated httpx client (analyst role)."""
    from app.main import create_app
    app = create_app()
    async with _make_client(app, db, test_user) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db: AsyncSession, admin_user: User):
    """Authenticated httpx client (admin role)."""
    from app.main import create_app
    app = create_app()
    async with _make_client(app, db, admin_user) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client(db: AsyncSession):
    """Unauthenticated httpx client (no user override — for auth tests)."""
    from app.main import create_app
    app = create_app()

    async def _override_db():
        yield db

    app.dependency_overrides[get_db] = _override_db
    # Do NOT override get_current_user — routes requiring auth will fail naturally
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_token(test_user: User) -> str:
    """JWT token for the test_user."""
    return create_access_token(test_user.id, test_user.role)


@pytest_asyncio.fixture
async def admin_auth_token(admin_user: User) -> str:
    """JWT token for the admin_user."""
    return create_access_token(admin_user.id, admin_user.role)
