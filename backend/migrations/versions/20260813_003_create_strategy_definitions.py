"""Create immutable Strategy Definition storage.

Revision ID: 20260813_003_strategy
Revises: 0001_historical_market_data
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260813_003_strategy"
down_revision: str | None = "0001_historical_market_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_type", sa.String(length=32), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("contract_version", sa.String(length=32), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parameter_schema_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(content_fingerprint) = 64",
            name="ck_strategy_definitions_content_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(parameter_schema_fingerprint) = 64",
            name="ck_strategy_definitions_parameter_schema_fingerprint_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_strategy_definitions"),
        sa.UniqueConstraint(
            "content_fingerprint",
            name="uq_strategy_definitions_content_fingerprint",
        ),
    )
    op.create_index(
        "ix_strategy_definitions_strategy_version",
        "strategy_definitions",
        ["strategy_id", "strategy_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_definitions_strategy_version",
        table_name="strategy_definitions",
    )
    op.drop_table("strategy_definitions")
