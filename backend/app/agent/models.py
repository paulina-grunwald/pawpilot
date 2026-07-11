from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentThread(Base):
    __tablename__ = "agent_threads"

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
