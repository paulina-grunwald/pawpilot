"""Create tractive_day_rollup and tractive_raw_payload tables.

Revision ID: 0003_create_tractive_tables
Revises: 0002_create_pets
Create Date: 2026-05-23

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0003_create_tractive_tables"
down_revision: str | None = "0002_create_pets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tractive_day_rollup",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("pet_id", GUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("minutes_active", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("minutes_low_intensity", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("minutes_moderate", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("minutes_night_sleep", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("minutes_day_sleep", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("minutes_no_signal", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "hourly_minutes_by_category",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "heart_rate_n_samples", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("heart_rate_mean", sa.Float(), nullable=True),
        sa.Column("heart_rate_min", sa.Float(), nullable=True),
        sa.Column("heart_rate_max", sa.Float(), nullable=True),
        sa.Column(
            "heart_rate_samples", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column(
            "respiratory_rate_n_samples", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("respiratory_rate_mean", sa.Float(), nullable=True),
        sa.Column("respiratory_rate_min", sa.Float(), nullable=True),
        sa.Column("respiratory_rate_max", sa.Float(), nullable=True),
        sa.Column(
            "respiratory_rate_samples",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("gps_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("gps_distance_km", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "gps_segments_counted", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "gps_segments_dropped", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("gps_by_sensor", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("gps_first_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gps_last_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("battery_min", sa.Integer(), nullable=True),
        sa.Column("battery_max", sa.Integer(), nullable=True),
        sa.Column("temperature_min", sa.Float(), nullable=True),
        sa.Column("temperature_max", sa.Float(), nullable=True),
        sa.Column("n_charging_starts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pet_id", "date", name="uq_tractive_day_rollup_pet_date"),
        sa.CheckConstraint(
            "source in ('gdpr_export', 'live_api')",
            name="ck_tractive_day_rollup_source_enum",
        ),
    )
    op.create_index("ix_tractive_day_rollup_pet_id", "tractive_day_rollup", ["pet_id"])

    op.create_table(
        "tractive_raw_payload",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("pet_id", GUID(), nullable=False),
        sa.Column("payload_type", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("date_range_start", sa.Date(), nullable=True),
        sa.Column("date_range_end", sa.Date(), nullable=True),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("ingest_batch_id", GUID(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "source in ('gdpr_export', 'live_api')",
            name="ck_tractive_raw_payload_source_enum",
        ),
        sa.CheckConstraint(
            "payload_type in ("
            "'activity_data', 'position_reports', 'hardware_reports', "
            "'resting_heart_rates', 'resting_respiratory_rates'"
            ")",
            name="ck_tractive_raw_payload_type_enum",
        ),
    )
    op.create_index("ix_tractive_raw_payload_pet_id", "tractive_raw_payload", ["pet_id"])
    op.create_index(
        "ix_tractive_raw_payload_ingest_batch_id",
        "tractive_raw_payload",
        ["ingest_batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tractive_raw_payload_ingest_batch_id", table_name="tractive_raw_payload")
    op.drop_index("ix_tractive_raw_payload_pet_id", table_name="tractive_raw_payload")
    op.drop_table("tractive_raw_payload")
    op.drop_index("ix_tractive_day_rollup_pet_id", table_name="tractive_day_rollup")
    op.drop_table("tractive_day_rollup")
