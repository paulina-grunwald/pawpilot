"""GET/PATCH /users/me — user story 2, scenarios 4, 5, 6, 9."""

from __future__ import annotations

from datetime import datetime

from httpx import AsyncClient


async def test_get_me_with_valid_cookie_returns_user_record(
    authenticated_client: AsyncClient, registered_user: dict[str, str]
) -> None:
    response = await authenticated_client.get("/users/me")

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == registered_user["email"]
    assert body["is_active"] is True
    assert body["is_verified"] is False
    assert isinstance(body["id"], str)
    # created_at must be a parseable ISO-8601 timestamp.
    datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))
    assert set(body.keys()) == {"id", "email", "is_active", "is_verified", "created_at"}


async def test_get_me_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_get_me_with_tampered_cookie_returns_401(
    authenticated_client: AsyncClient,
) -> None:

    import jwt

    from app.config import settings

    original = authenticated_client.cookies["pawpilot_auth"]
    payload = jwt.decode(original, options={"verify_signature": False})
    forged = jwt.encode(payload, settings.jwt_secret + "-attacker", algorithm="HS256")
    authenticated_client.cookies.set("pawpilot_auth", forged)

    response = await authenticated_client.get("/users/me")
    assert response.status_code == 401


async def test_get_me_with_garbage_cookie_returns_401(client: AsyncClient) -> None:
    client.cookies.set("pawpilot_auth", "not-even-a-jwt")
    response = await client.get("/users/me")
    assert response.status_code == 401


async def test_patch_me_updates_password(
    authenticated_client: AsyncClient, registered_user: dict[str, str]
) -> None:
    new_password = "brand-new-passphrase"
    patch_response = await authenticated_client.patch("/users/me", json={"password": new_password})
    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["email"] == registered_user["email"]
    assert "hashed_password" not in body
    assert "password" not in body

    # Old password no longer works.
    authenticated_client.cookies.clear()
    old_login = await authenticated_client.post(
        "/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert old_login.status_code == 400
    assert old_login.json() == {"detail": "LOGIN_BAD_CREDENTIALS"}

    # New password works.
    new_login = await authenticated_client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": new_password},
    )
    assert new_login.status_code == 204
    assert "pawpilot_auth" in new_login.cookies


async def test_patch_me_short_password_returns_400(
    authenticated_client: AsyncClient,
) -> None:
    response = await authenticated_client.patch("/users/me", json={"password": "abc"})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "UPDATE_USER_INVALID_PASSWORD"


async def test_patch_me_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.patch("/users/me", json={"password": "newvalidpass"})
    assert response.status_code == 401
