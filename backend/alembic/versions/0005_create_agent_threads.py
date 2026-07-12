"""Create agent_threads table.

Revision ID: 0005_create_agent_threads
Revises: 0004_create_journal_entries
Create Date: 2026-07-12

Tracks each Ask PawPilot conversation: its owner, the dog it is about, and atitle, so the frontend can list a user's past conversations. The messages themselves live in the LangGraph checkpoint tables (created by the checkpointer's own setup), keyed by ``thread_id``. This table previously existed only in the
test schema (``create_all``); this migration brings it to real deployments.

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID

from alembic import op

revision: str = "0005_create_agent_threads"
down_revision: str | None = "0004_create_journal_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_threads",
        sa.Column("thread_id", sa.String(length=255), nullable=False),
        sa.Column("owner_user_id", GUID(), nullable=False),
        sa.Column("pet_id", GUID(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("thread_id"),
    )
    op.create_index("ix_agent_threads_owner_user_id", "agent_threads", ["owner_user_id"])
    op.create_index("ix_agent_threads_pet_id", "agent_threads", ["pet_id"])
    op.create_index("ix_agent_threads_updated_at", "agent_threads", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_threads_updated_at", table_name="agent_threads")
    op.drop_index("ix_agent_threads_pet_id", table_name="agent_threads")
    op.drop_index("ix_agent_threads_owner_user_id", table_name="agent_threads")
    op.drop_table("agent_threads")
