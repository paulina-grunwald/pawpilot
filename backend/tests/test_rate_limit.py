"""Unit tests for the rate-limit key logic (enforcement is covered in test_router)."""

from __future__ import annotations

from starlette.requests import Request

from app.rate_limit import rate_limit_key, set_user_rate_limit_key


def _request(client_ip: str = "203.0.113.7") -> Request:
    return Request({"type": "http", "headers": [], "client": (client_ip, 12345)})


def test_key_falls_back_to_client_ip_when_unstashed() -> None:
    assert rate_limit_key(_request("203.0.113.7")) == "203.0.113.7"


def test_key_uses_user_id_once_stashed() -> None:
    request = _request()
    set_user_rate_limit_key(request, "user-abc")
    assert rate_limit_key(request) == "user:user-abc"


def test_stashed_user_key_shadows_the_ip() -> None:
    request = _request("203.0.113.7")
    set_user_rate_limit_key(request, 42)
    assert rate_limit_key(request) == "user:42"
