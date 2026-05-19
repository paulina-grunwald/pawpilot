"""POST /auth/login — user story 2, scenarios 3 and 7."""

from __future__ import annotations

from httpx import AsyncClient


async def test_login_with_correct_credentials_sets_cookie(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    response = await client.post(
        "/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    assert "pawpilot_auth" in response.cookies

    set_cookie_header = response.headers.get("set-cookie", "")
    assert "pawpilot_auth=" in set_cookie_header
    assert "HttpOnly" in set_cookie_header
    # Dev environment is not over HTTPS, so the cookie must not be Secure here.
    assert "Secure" not in set_cookie_header
    assert "samesite=lax" in set_cookie_header.lower()
    assert "Path=/" in set_cookie_header

    cookie_value = response.cookies["pawpilot_auth"]
    # JWT shape: three base64url segments separated by dots.
    assert cookie_value.count(".") == 2


async def test_login_with_wrong_password_returns_400_bad_credentials(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    response = await client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": "wrong-password"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "LOGIN_BAD_CREDENTIALS"}
    assert "pawpilot_auth" not in response.cookies


async def test_login_with_unknown_email_returns_same_response(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """No enumeration leak — unknown email and wrong password are indistinguishable."""
    wrong_password = await client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": "wrong-password"},
    )
    unknown_email = await client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "wrong-password"},
    )

    assert wrong_password.status_code == unknown_email.status_code == 400
    assert wrong_password.json() == unknown_email.json() == {"detail": "LOGIN_BAD_CREDENTIALS"}


async def test_login_requires_form_encoded_body(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """fastapi-users login uses OAuth2 password form — JSON should be rejected."""
    response = await client.post(
        "/auth/login",
        json={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 422
