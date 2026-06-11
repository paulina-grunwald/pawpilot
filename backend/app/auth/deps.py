from __future__ import annotations

from app.auth.router import fastapi_users

current_active_user = fastapi_users.current_user(active=True)
