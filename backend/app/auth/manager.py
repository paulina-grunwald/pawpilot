"""User manager — registration, login, and password validation.

Password reset is intentionally not wired (no `forgot_password` /
`reset_password` overrides, no reset router mounted). See todo.md.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import Depends
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.db.base import get_session

MIN_PASSWORD_LENGTH = 8

# `BaseUserManager` requires both secrets to be set on subclasses even when
# the reset and verification routers are not mounted. Hardcoded placeholders
# are safe here because no code path on this manager generates or accepts
# either token type — the corresponding `*_password` / `*verify` methods are
# never called. See todo.md.
_DISABLED_TOKEN_SECRET = "disabled-not-wired"


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = _DISABLED_TOKEN_SECRET
    verification_token_secret = _DISABLED_TOKEN_SECRET

    async def validate_password(self, password: str, user: User | Any) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise exceptions.InvalidPasswordException(
                reason=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )


async def get_user_db(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(get_user_db),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db)
