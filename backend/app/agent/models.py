from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentThread(Base):
    """One conversation thread: its owner, the dog it is about, and a title.

    ``pet_id`` and ``title`` power the "past conversations" history list; the
    conversation's messages themselves live in the LangGraph checkpoint tables,
    keyed by ``thread_id``. ``updated_at`` also drives stale-thread retention.
    """

    __tablename__ = "agent_threads"

    thread_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    pet_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("pets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
