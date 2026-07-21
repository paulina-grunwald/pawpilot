"""Shared rate limiter for the cost-sensitive agent routes.

The agent endpoints call the paid LLM gateway on every request, so an
authenticated user or a leaked token can spend real money by hammering them.
`limiter` caps that, keyed per authenticated user (falling back to client IP for
any unauthenticated route that opts in). Limits and the on/off switch come from
settings, so tests disable it and production tunes it without code changes.

Storage is in-process, which is correct for the single-container deployment; a
multi-replica deployment would need a shared backend (Redis) passed as
``storage_uri``. Documented rather than hidden.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings

_USER_KEY_ATTRIBUTE = "rate_limit_key"


def rate_limit_key(request: Request) -> str:
    """Per-user when an authenticated route stashed the id, else per client IP."""
    stashed = getattr(request.state, _USER_KEY_ATTRIBUTE, None)
    if stashed:
        return str(stashed)
    return get_remote_address(request)


def set_user_rate_limit_key(request: Request, user_id: object) -> None:
    """Tag the request so the limiter buckets it by user rather than by IP."""
    setattr(request.state, _USER_KEY_ATTRIBUTE, f"user:{user_id}")


limiter = Limiter(key_func=rate_limit_key, enabled=settings.rate_limit_enabled)
