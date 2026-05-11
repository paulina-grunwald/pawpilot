"""Pydantic request/response schemas for auth endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import Field


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
    ``is_verified`` from non-superuser updates. The spec only exercises
    password updates (email change is deferred); password validation runs
    through ``UserManager.validate_password`` so failures surface as
    ``UPDATE_USER_INVALID_PASSWORD``, not a 422.
    """
