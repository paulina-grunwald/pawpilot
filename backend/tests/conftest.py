"""Shared fixtures for the backend test suite.

The fixtures here implement the test-isolation contract from
`specs/002-infra-db-auth.md`:

  * One ephemeral Postgres per test *session*, brought up via testcontainers
    so tests exercise the same engine as production.
  * Full schema recreate once at session start (SQLAlchemy ``create_all``;
    Alembic migrations have their own dedicated test elsewhere).
  * Transaction-rollback per test — every test runs inside an outer
    transaction that is rolled back on teardown. Sessions handed to the
    application use ``join_transaction_mode="create_savepoint"`` so
    ``session.commit()`` inside endpoint code commits a SAVEPOINT, not the
    outer transaction.
"""

from __future__ import annotations

import os


os.environ["DATABASE_URL"] = "postgresql+asyncpg://placeholder:placeholder@localhost/placeholder"
os.environ["JWT_SECRET"] = "test-jwt-secret-32-bytes-of-padding"
os.environ["FRONTEND_BASE_URL"] = "http://localhost:3000"

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16") as container:
        yield container


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    # testcontainers hands back a psycopg2-style URL; swap the driver for asyncpg.
    raw_url: str = str(postgres_container.get_connection_url())
    if raw_url.startswith("postgresql+psycopg2://"):
        return raw_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_url


@pytest_asyncio.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    import app.auth.models
    from app.db.base import Base

    test_engine = create_async_engine(database_url, future=True)
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield test_engine
    finally:
        await test_engine.dispose()



@pytest_asyncio.fixture
async def db_connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.connect() as connection:
        outer_transaction = await connection.begin()
        try:
            yield connection
        finally:
            await outer_transaction.rollback()


@pytest_asyncio.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """Session for the test body itself — used for direct DB assertions."""
    factory = async_sessionmaker(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    async with factory() as session:
        yield session



@pytest_asyncio.fixture
async def client(db_connection: AsyncConnection) -> AsyncIterator[AsyncClient]:
    """Async HTTP client whose backing app uses the test DB.

    Each request inside an endpoint gets a *fresh* SQLAlchemy session bound to
    the same underlying connection as `db_session`, so:

      * Endpoint code commits go to a SAVEPOINT and are visible to the test.
      * The outer transaction is rolled back when the test finishes, leaving
        the database clean for the next test.
    """
    from app.db.base import get_session
    from app.main import app

    request_factory = async_sessionmaker(
        bind=db_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        async with request_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client
    finally:
        app.dependency_overrides.pop(get_session, None)



@pytest_asyncio.fixture
async def registered_user(client: AsyncClient) -> dict[str, str]:
    """Create a user via /auth/register and return the credentials used."""
    credentials = {"email": "alice@example.com", "password": "correct-horse-battery"}
    response = await client.post("/auth/register", json=credentials)
    assert response.status_code == 201, response.text
    return credentials


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, registered_user: dict[str, str]) -> AsyncClient:
    """Client that has already logged in — cookie is in the jar."""
    login_response = await client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    assert login_response.status_code == 204, login_response.text
    assert "pawpilot_auth" in client.cookies
    return client
