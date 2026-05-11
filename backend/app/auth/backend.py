"""Authentication backend: cookie transport + JWT strategy."""

from __future__ import annotations

import uuid

from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy

from app.auth.models import User
from app.config import settings

cookie_transport = CookieTransport(
    cookie_name=settings.cookie_name,
    cookie_max_age=settings.cookie_max_age_seconds,
    cookie_secure=settings.cookie_secure,
    cookie_httponly=True,
    cookie_samesite=settings.cookie_samesite,
)


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    return JWTStrategy(
        secret=settings.jwt_secret,
        lifetime_seconds=settings.jwt_lifetime_seconds,
        algorithm="HS256",
    )


auth_backend: AuthenticationBackend[User, uuid.UUID] = AuthenticationBackend(
    name="cookie-jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
