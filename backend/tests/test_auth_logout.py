"""POST /auth/logout — user story 2, scenario 8."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from httpx import AsyncClient


async def test_logout_clears_cookie(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.post("/auth/logout")

    assert response.status_code == 204
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "pawpilot_auth=" in set_cookie_header
    # The cookie must be invalidated. fastapi-users does this either by
    # emitting an empty value or by setting an expiry in the past — accept
    # either, but it MUST NOT carry a future expiry.
    has_empty_value = (
        'pawpilot_auth=""' in set_cookie_header or "pawpilot_auth=;" in set_cookie_header
    )
    has_past_expiry = False
    for raw_piece in set_cookie_header.split(";"):
        piece = raw_piece.strip()
        if piece.lower().startswith("expires="):
            expires_at = parsedate_to_datetime(piece.split("=", 1)[1])
            has_past_expiry = expires_at < datetime.now(UTC)
        if piece.lower() == "max-age=0":
            has_past_expiry = True
    assert has_empty_value or has_past_expiry, set_cookie_header

    # After logout the httpx jar reflects the cleared cookie.
    assert authenticated_client.cookies.get("pawpilot_auth") in (None, "", '""')


async def test_logout_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.post("/auth/logout")
    assert response.status_code == 401


async def test_logout_then_me_returns_401(authenticated_client: AsyncClient) -> None:
    logout_response = await authenticated_client.post("/auth/logout")
    assert logout_response.status_code == 204

    me_response = await authenticated_client.get("/users/me")
    assert me_response.status_code == 401
