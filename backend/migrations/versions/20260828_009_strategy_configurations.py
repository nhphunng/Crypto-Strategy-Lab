"""Persist immutable saved strategy configurations and ordered members.

Revision ID: 20260828_009_strategy_configs
Revises: 20260828_008_failure_reason
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260828_009_strategy_configs"
down_revision: str | None = "20260828_008_failure_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_strategy_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_key", sa.String(length=64), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("root_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("pair", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("combination", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["root_definition_id"], ["strategy_definitions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "configuration_key",
            "configuration_version",
            name="uq_saved_strategy_configurations_key_version",
        ),
        sa.UniqueConstraint(
            "content_fingerprint",
            name="uq_saved_strategy_configurations_content_fingerprint",
        ),
    )
    op.create_index(
        "ix_saved_strategy_configurations_created",
        "saved_strategy_configurations",
        ["created_at", "id"],
    )
    op.create_table(
        "saved_strategy_configuration_members",
        sa.Column("configuration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("definition_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weight", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["configuration_id"], ["saved_strategy_configurations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["definition_id"], ["strategy_definitions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("configuration_id", "position"),
    )


def downgrade() -> None:
    op.drop_table("saved_strategy_configuration_members")
    op.drop_index(
        "ix_saved_strategy_configurations_created",
        table_name="saved_strategy_configurations",
    )
    op.drop_table("saved_strategy_configurations")
