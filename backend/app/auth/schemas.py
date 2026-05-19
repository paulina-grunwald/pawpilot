"""Pydantic request/response schemas for auth endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import Field, field_validator


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Shape returned by /auth/register, GET /users/me, PATCH /users/me.

    Inherits ``schemas.BaseUser`` to satisfy fastapi-users' type bound but
    hides ``is_superuser`` from the response — the spec's UserRead is
    ``{id, email, is_active, is_verified, created_at}``.
    """

    created_at: datetime
    is_superuser: bool = Field(default=False, exclude=True)


class UserCreate(schemas.BaseUserCreate):
    """POST /auth/register body — fastapi-users default fields."""


class UserUpdate(schemas.BaseUserUpdate):
    """PATCH /users/me body.

    Inherits fastapi-users' update schema so the framework's safe
    ``create_update_dict`` strips ``is_active`` / ``is_superuser`` /
    ``is_verified`` from non-superuser updates. Password validation runs
    through ``UserManager.validate_password`` so failures surface as
    ``UPDATE_USER_INVALID_PASSWORD``, not a 422.
    """

    @field_validator("email")
    @classmethod
    def _reject_email_change(cls, value: str | None) -> None:
        if value is not None:
            raise ValueError(
                "Changing email is not yet supported — a dedicated verification flow is required."
            )
        return None
