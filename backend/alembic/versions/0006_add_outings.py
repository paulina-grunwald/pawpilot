"""Add outing columns to tractive_day_rollup.

Revision ID: 0006_add_outings
Revises: 0005_add_record_level_vitals
Create Date: 2026-07-17

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0006_add_outings"
down_revision: str | None = "0005_add_record_level_vitals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "tractive_day_rollup"


def upgrade() -> None:
    op.add_column(
        _TABLE,
        sa.Column("outings_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        _TABLE,
        sa.Column("outings_total_minutes", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        _TABLE,
        sa.Column("outings", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(_TABLE, sa.Column("home_latitude", sa.Float(), nullable=True))
    op.add_column(_TABLE, sa.Column("home_longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column(_TABLE, "home_longitude")
    op.drop_column(_TABLE, "home_latitude")
    op.drop_column(_TABLE, "outings")
    op.drop_column(_TABLE, "outings_total_minutes")
    op.drop_column(_TABLE, "outings_count")
