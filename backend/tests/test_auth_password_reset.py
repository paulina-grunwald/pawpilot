"""POST /auth/forgot-password + /auth/reset-password — user story 3, scenarios 1-9.

Reset tokens are forged in-test by reading the JTI persisted on the user row
by ``/auth/forgot-password`` and signing an equivalent JWT with the same
secret + audience + JTI. This mirrors what ``UserManager.forgot_password``
produces internally and lets us cover the full reset flow without an email
provider wired up (see todo.md).
"""

from __future__ import annotations

import time
import uuid

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import settings


def _forge_reset_token(user_id: uuid.UUID, jti: str) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "aud": settings.reset_password_token_audience,
            "jti": jti,
            "exp": int(time.time()) + settings.reset_password_token_lifetime_seconds,
        },
        settings.reset_password_token_secret,
        algorithm="HS256",
    )


async def _load_user(db_session: AsyncSession, email: str) -> User:
    """Re-read the user row, bypassing the identity-map cache."""
    result = await db_session.execute(
        select(User)
        .where(User.email == email)  # type: ignore[arg-type]
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def _issue_reset_token(client: AsyncClient, db_session: AsyncSession, email: str) -> str:
    """Call /auth/forgot-password then forge an equivalent JWT from the persisted JTI."""
    response = await client.post("/auth/forgot-password", json={"email": email})
    assert response.status_code == 202
    user_row = await _load_user(db_session, email)
    assert user_row.reset_token_jti is not None
    return _forge_reset_token(user_row.id, user_row.reset_token_jti)


async def test_forgot_password_known_email_persists_new_jti(
    client: AsyncClient,
    db_session: AsyncSession,
    registered_user: dict[str, str],
) -> None:
    user_before = await _load_user(db_session, registered_user["email"])
    assert user_before.reset_token_jti is None

    response = await client.post("/auth/forgot-password", json={"email": registered_user["email"]})
    assert response.status_code == 202

    user_after = await _load_user(db_session, registered_user["email"])
    assert user_after.reset_token_jti is not None
    assert user_after.reset_token_jti != ""


async def test_forgot_password_unknown_email_is_byte_identical(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """Enumeration defense — known and unknown emails respond identically."""
    known = await client.post("/auth/forgot-password", json={"email": registered_user["email"]})
    unknown = await client.post("/auth/forgot-password", json={"email": "nobody@example.com"})

    assert known.status_code == unknown.status_code == 202
    assert known.content == unknown.content
    for header_name in ("content-type", "content-length"):
        assert known.headers.get(header_name) == unknown.headers.get(header_name)


async def test_forgot_password_malformed_payload_returns_422(client: AsyncClient) -> None:
    response = await client.post("/auth/forgot-password", json={"email": 12345})
    assert response.status_code == 422


async def test_reset_password_with_valid_token_updates_hash(
    client: AsyncClient,
    db_session: AsyncSession,
    registered_user: dict[str, str],
) -> None:
    token = await _issue_reset_token(client, db_session, registered_user["email"])

    user_before = await _load_user(db_session, registered_user["email"])
    hash_before = user_before.hashed_password

    response = await client.post(
        "/auth/reset-password",
        json={"token": token, "password": "freshpassword1"},
    )
    assert response.status_code == 200

    user_after = await _load_user(db_session, registered_user["email"])
    assert user_after.hashed_password != hash_before
    assert user_after.hashed_password.startswith("$argon2")


async def test_reset_password_single_use_token_cannot_be_reused(
    client: AsyncClient, db_session: AsyncSession, registered_user: dict[str, str]
) -> None:
    token = await _issue_reset_token(client, db_session, registered_user["email"])

    first = await client.post(
        "/auth/reset-password", json={"token": token, "password": "freshpassword1"}
    )
    assert first.status_code == 200

    second = await client.post(
        "/auth/reset-password", json={"token": token, "password": "anotherpassword2"}
    )
    assert second.status_code == 400
    assert second.json() == {"detail": "RESET_PASSWORD_BAD_TOKEN"}


async def test_reset_password_expired_token_is_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    registered_user: dict[str, str],
) -> None:
    """Forge an expired JWT signed with the same secret/audience as the app."""
    user_row = await _load_user(db_session, registered_user["email"])

    expired_payload = {
        "sub": str(user_row.id),
        "aud": settings.reset_password_token_audience,
        # Issued 2 hours ago, expired 1 hour ago.
        "exp": 1_700_000_000,
        "iat": 1_699_996_400,
        "jti": "any-jti",
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.reset_password_token_secret,
        algorithm="HS256",
    )

    response = await client.post(
        "/auth/reset-password",
        json={"token": expired_token, "password": "freshpassword1"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "RESET_PASSWORD_BAD_TOKEN"}


@pytest.mark.parametrize(
    "bad_token",
    [
        "not-a-jwt-at-all",
        "aaa.bbb.ccc",
        # Valid shape, wrong signature. Secret is padded to 32 bytes so pyjwt
        # doesn't emit InsecureKeyLengthWarning during test collection.
        jwt.encode(
            {"sub": "x", "aud": "fastapi-users:reset"},
            "wrong-secret-padded-to-32-bytes!!",
            algorithm="HS256",
        ),
    ],
)
async def test_reset_password_invalid_token_returns_bad_token(
    client: AsyncClient, bad_token: str
) -> None:
    response = await client.post(
        "/auth/reset-password",
        json={"token": bad_token, "password": "freshpassword1"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "RESET_PASSWORD_BAD_TOKEN"}


async def test_reset_password_short_password_returns_invalid_password(
    client: AsyncClient, db_session: AsyncSession, registered_user: dict[str, str]
) -> None:
    token = await _issue_reset_token(client, db_session, registered_user["email"])

    response = await client.post("/auth/reset-password", json={"token": token, "password": "abc"})
    assert response.status_code == 400
    detail = response.json()["detail"]
    # fastapi-users returns either a bare code or an object with a "code" key
    # depending on whether the policy hook produced a reason.
    code = detail["code"] if isinstance(detail, dict) else detail
    assert code == "RESET_PASSWORD_INVALID_PASSWORD"


async def test_reset_password_full_login_roundtrip(
    client: AsyncClient, db_session: AsyncSession, registered_user: dict[str, str]
) -> None:
    new_password = "totally-different-pw"
    token = await _issue_reset_token(client, db_session, registered_user["email"])

    reset_response = await client.post(
        "/auth/reset-password", json={"token": token, "password": new_password}
    )
    assert reset_response.status_code == 200

    # Old password no longer logs in.
    old_login = await client.post(
        "/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert old_login.status_code == 400
    assert old_login.json() == {"detail": "LOGIN_BAD_CREDENTIALS"}

    # New password does.
    new_login = await client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": new_password},
    )
    assert new_login.status_code == 204
    assert "pawpilot_auth" in new_login.cookies


async def test_two_resets_in_a_row_first_token_is_invalidated(
    client: AsyncClient, db_session: AsyncSession, registered_user: dict[str, str]
) -> None:
    """Newest JTI wins — earlier reset tokens must stop working as soon as a new one is issued."""
    first_token = await _issue_reset_token(client, db_session, registered_user["email"])
    second_token = await _issue_reset_token(client, db_session, registered_user["email"])
    assert second_token != first_token

    use_first = await client.post(
        "/auth/reset-password",
        json={"token": first_token, "password": "freshpassword1"},
    )
    assert use_first.status_code == 400
    assert use_first.json() == {"detail": "RESET_PASSWORD_BAD_TOKEN"}

    # The newest one still works.
    use_second = await client.post(
        "/auth/reset-password",
        json={"token": second_token, "password": "freshpassword2"},
    )
    assert use_second.status_code == 200
