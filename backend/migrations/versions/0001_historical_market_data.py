"""Create immutable historical Candle and dataset tables.

Revision ID: 0001_historical_market_data
Revises: None
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_historical_market_data"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("pair", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("high", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("low", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("close", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("volume", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("closed", sa.Boolean(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "high >= open AND high >= low AND high >= close", name="ck_candles_high"
        ),
        sa.CheckConstraint("closed = true", name="ck_candles_historical_closed"),
        sa.CheckConstraint("low <= open AND low <= high AND low <= close", name="ck_candles_low"),
        sa.CheckConstraint(
            "open > 0 AND high > 0 AND low > 0 AND close > 0",
            name="ck_candles_prices_positive",
        ),
        sa.CheckConstraint("volume >= 0", name="ck_candles_volume_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider", "pair", "timeframe", "open_time", name="uq_candles_identity"
        ),
    )
    op.create_index(
        "ix_candles_selection_open",
        "candles",
        ["provider", "pair", "timeframe", "open_time"],
        unique=False,
    )
    op.create_table(
        "candle_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_key", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("pair", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("candle_count", sa.Integer(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("build_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status <> 'BUILDING') OR (build_token IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_candle_datasets_build_fields",
        ),
        sa.CheckConstraint(
            "(status <> 'COMPLETE') OR (candle_count > 0 AND checksum IS NOT NULL "
            "AND completed_at IS NOT NULL AND build_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_candle_datasets_complete_fields",
        ),
        sa.CheckConstraint(
            "status IN ('BUILDING','COMPLETE','INCOMPLETE','FAILED')",
            name="ck_candle_datasets_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_key", name="uq_candle_datasets_request_key"),
        sa.UniqueConstraint(
            "schema_version",
            "provider",
            "pair",
            "timeframe",
            "start_time",
            "end_time",
            name="uq_candle_datasets_selection_range",
        ),
    )
    op.create_index(
        "ix_candle_datasets_selection_range",
        "candle_datasets",
        ["provider", "pair", "timeframe", "start_time", "end_time"],
        unique=False,
    )
    op.create_index(
        "ix_candle_datasets_status_lease",
        "candle_datasets",
        ["status", "lease_expires_at"],
        unique=False,
    )
    op.create_table(
        "candle_dataset_members",
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("position >= 0", name="ck_dataset_member_position"),
        sa.ForeignKeyConstraint(["candle_id"], ["candles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dataset_id"], ["candle_datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("dataset_id", "position"),
        sa.UniqueConstraint("dataset_id", "candle_id", name="uq_dataset_member_candle"),
    )


def downgrade() -> None:
    op.drop_table("candle_dataset_members")
    op.drop_index("ix_candle_datasets_status_lease", table_name="candle_datasets")
    op.drop_index("ix_candle_datasets_selection_range", table_name="candle_datasets")
    op.drop_table("candle_datasets")
    op.drop_index("ix_candles_selection_open", table_name="candles")
    op.drop_table("candles")
