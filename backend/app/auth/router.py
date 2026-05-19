"""Mounts the fastapi-users routers under /auth and /users."""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from fastapi_users import FastAPIUsers

from app.auth.backend import auth_backend
from app.auth.manager import get_user_manager
from app.auth.models import User
from app.auth.schemas import UserCreate, UserRead, UserUpdate

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

auth_router = APIRouter(prefix="/auth", tags=["auth"])
auth_router.include_router(fastapi_users.get_auth_router(auth_backend))
auth_router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))
# Password-reset router intentionally not mounted — see todo.md.

users_router = APIRouter(prefix="/users", tags=["users"])
users_router.include_router(fastapi_users.get_users_router(UserRead, UserUpdate))
