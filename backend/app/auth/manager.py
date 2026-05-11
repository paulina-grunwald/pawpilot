"""User manager — overrides forgot/reset password to enforce JTI single-use.

fastapi-users' default reset flow embeds a ``password_fgpt`` claim that
invalidates a token *after* its first successful use (the hash changes). That
covers happy-path single-use, but it does NOT invalidate older tokens when a
new reset is requested. The spec's "newest JTI wins" rule needs an explicit
JTI persisted on the user row, which is what these overrides add.
"""

from __future__ import annotations

import secrets
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import jwt as pyjwt
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions
from fastapi_users.jwt import decode_jwt, generate_jwt
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.config import settings
from app.db.base import get_session
from app.email.sender import EmailSender, get_email_sender

MIN_PASSWORD_LENGTH = 8


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.reset_password_token_secret
    reset_password_token_lifetime_seconds = settings.reset_password_token_lifetime_seconds
    reset_password_token_audience = settings.reset_password_token_audience

    # Verification flow is deferred (open question in the spec); the secret is
    # still required by BaseUserManager so we reuse the reset secret as a
    # harmless placeholder. No verification endpoint is mounted.
    verification_token_secret = settings.reset_password_token_secret

    def __init__(self, user_db: SQLAlchemyUserDatabase[User, uuid.UUID], email_sender: EmailSender):
        super().__init__(user_db)
        self.email_sender = email_sender

    async def validate_password(self, password: str, user: User | Any) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise exceptions.InvalidPasswordException(
                reason=f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )

    async def on_after_register(self, user: User, request: Request | None = None) -> None:
        # Hook reserved for welcome-email work in a follow-up spec.
        return None

    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        reset_url = f"{settings.frontend_base_url}/reset-password?token={token}"
        await self.email_sender.send_password_reset(user.email, reset_url)

    async def on_after_reset_password(self, user: User, request: Request | None = None) -> None:
        return None

    async def forgot_password(self, user: User, request: Request | None = None) -> None:
        if not user.is_active:
            raise exceptions.UserInactive()

        jti = secrets.token_urlsafe(16)
        # Persist the new JTI first — any previously-issued token is now invalid.
        await self.user_db.update(user, {"reset_token_jti": jti})

        token = generate_jwt(
            {
                "sub": str(user.id),
                "aud": self.reset_password_token_audience,
                "jti": jti,
            },
            self.reset_password_token_secret,
            self.reset_password_token_lifetime_seconds,
        )
        await self.on_after_forgot_password(user, token, request)

    async def reset_password(
        self, token: str, password: str, request: Request | None = None
    ) -> User:
        try:
            data = decode_jwt(
                token,
                self.reset_password_token_secret,
                [self.reset_password_token_audience],
            )
        except pyjwt.PyJWTError as error:
            raise exceptions.InvalidResetPasswordToken() from error

        user_id_raw = data.get("sub")
        token_jti = data.get("jti")
        if not isinstance(user_id_raw, str) or not isinstance(token_jti, str):
            raise exceptions.InvalidResetPasswordToken()

        try:
            parsed_id = self.parse_id(user_id_raw)
        except exceptions.InvalidID as error:
            raise exceptions.InvalidResetPasswordToken() from error

        try:
            user = await self.get(parsed_id)
        except exceptions.UserNotExists as error:
            raise exceptions.InvalidResetPasswordToken() from error

        if user.reset_token_jti != token_jti:
            raise exceptions.InvalidResetPasswordToken()

        if not user.is_active:
            raise exceptions.UserInactive()

        # `_update` calls validate_password — short passwords surface as
        # `InvalidPasswordException`, which the router maps to
        # RESET_PASSWORD_INVALID_PASSWORD.
        updated_user = await self._update(user, {"password": password})
        # Clear the JTI — the token has now been spent.
        await self.user_db.update(updated_user, {"reset_token_jti": None})

        await self.on_after_reset_password(updated_user, request)
        return updated_user


async def get_user_db(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase[User, uuid.UUID], None]:
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase[User, uuid.UUID] = Depends(get_user_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> AsyncGenerator[UserManager, None]:
    yield UserManager(user_db, email_sender)
