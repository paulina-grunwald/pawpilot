"""POST /auth/register — user story 2, scenarios 1 and 2 + validation."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def test_register_creates_user_with_argon2_hash(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from app.auth.models import User

    response = await client.post(
        "/auth/register",
        json={"email": "newuser@example.com", "password": "supersecret"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert "id" in body
    assert "hashed_password" not in body
    assert "password" not in body

    stored = (
        await db_session.execute(
            select(User).where(User.email == "newuser@example.com")  # type: ignore[arg-type]
        )
    ).scalar_one()
    # Argon2 hashes always start with "$argon2" — confirms no plaintext storage.
    assert stored.hashed_password.startswith("$argon2"), stored.hashed_password
    assert stored.hashed_password != "supersecret"


async def test_register_duplicate_email_returns_400(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "supersecret"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201, first.text

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert second.json() == {"detail": "REGISTER_USER_ALREADY_EXISTS"}


async def test_register_password_too_short_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "abc"},
    )
    # fastapi-users surfaces password-policy failures as 400, not 422.
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"


async def test_register_invalid_email_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "supersecret"},
    )
    assert response.status_code == 422


async def test_register_response_omits_internal_columns(client: AsyncClient) -> None:
    """`hashed_password` and `reset_token_jti` must never appear in API output."""
    response = await client.post(
        "/auth/register",
        json={"email": "shape@example.com", "password": "supersecret"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"id", "email", "is_active", "is_verified", "created_at"}
