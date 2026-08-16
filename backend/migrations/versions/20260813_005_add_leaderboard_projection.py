"""Create durable leaderboard projection and update records.

Revision ID: 20260813_005_leaderboard
Revises: 20260813_004_backtest
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260813_005_leaderboard"
down_revision: str | None = "20260813_004_backtest"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leaderboards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_key", sa.String(length=512), nullable=False),
        sa.Column("scoring_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scoring_policy_version", sa.String(length=32), nullable=False),
        sa.Column("rank_metric", sa.String(length=32), nullable=False),
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("projection_version", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entry_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "entry_count >= 0 AND entry_count <= k",
            name="ck_leaderboards_entry_count",
        ),
        sa.CheckConstraint("k >= 1 AND k <= 200", name="ck_leaderboards_k_range"),
        sa.CheckConstraint(
            "projection_version >= 0",
            name="ck_leaderboards_projection_version",
        ),
        sa.CheckConstraint(
            "rank_metric IN "
            "('OVERALL_SCORE','TOTAL_RETURN','WIN_RATE','MAX_DRAWDOWN','SHARPE_RATIO')",
            name="ck_leaderboards_rank_metric",
        ),
        sa.ForeignKeyConstraint(
            ["scoring_policy_id"],
            ["scoring_policies.id"],
            name="fk_leaderboards_scoring_policy_id_scoring_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_run_id"],
            ["backtest_runs.id"],
            name="fk_leaderboards_source_run_id_backtest_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_leaderboards"),
        sa.UniqueConstraint(
            "scope_key",
            "scoring_policy_id",
            "scoring_policy_version",
            "rank_metric",
            "k",
            name="uq_leaderboards_identity",
        ),
    )
    op.create_index(
        "ix_leaderboards_updated_at",
        "leaderboards",
        ["updated_at"],
        unique=False,
    )
    op.create_table(
        "leaderboard_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leaderboard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("sort_key", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("projection_version", sa.BigInteger(), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "projection_version >= 0",
            name="ck_leaderboard_entries_projection_version",
        ),
        sa.CheckConstraint("rank > 0", name="ck_leaderboard_entries_rank"),
        sa.ForeignKeyConstraint(
            ["evaluation_result_id"],
            ["evaluation_results.id"],
            name="fk_leaderboard_entries_result_id_evaluation_results",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["leaderboard_id"],
            ["leaderboards.id"],
            name="fk_leaderboard_entries_leaderboard_id_leaderboards",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_leaderboard_entries"),
        sa.UniqueConstraint(
            "leaderboard_id",
            "evaluation_result_id",
            name="uq_leaderboard_entries_evaluation_result",
        ),
        sa.UniqueConstraint(
            "leaderboard_id",
            "rank",
            name="uq_leaderboard_entries_rank",
        ),
    )
    op.create_table(
        "leaderboard_update_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("leaderboard_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("projection_version", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column(
            "source_evaluation_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("added_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("removed_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("moved_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "event_type = 'LEADERBOARD_UPDATED'",
            name="ck_leaderboard_update_records_event_type",
        ),
        sa.CheckConstraint(
            "projection_version > 0",
            name="ck_leaderboard_update_records_projection_version",
        ),
        sa.ForeignKeyConstraint(
            ["leaderboard_id"],
            ["leaderboards.id"],
            name="fk_leaderboard_update_records_leaderboard_id_leaderboards",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_evaluation_result_id"],
            ["evaluation_results.id"],
            name="fk_leaderboard_update_records_result_id_evaluation_results",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_run_id"],
            ["backtest_runs.id"],
            name="fk_leaderboard_update_records_run_id_backtest_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_leaderboard_update_records"),
        sa.UniqueConstraint(
            "leaderboard_id",
            "projection_version",
            name="uq_leaderboard_update_records_projection_version",
        ),
    )
    op.create_index(
        "ix_leaderboard_update_records_publication",
        "leaderboard_update_records",
        ["published_at", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_leaderboard_update_records_publication",
        table_name="leaderboard_update_records",
    )
    op.drop_table("leaderboard_update_records")
    op.drop_table("leaderboard_entries")
    op.drop_index("ix_leaderboards_updated_at", table_name="leaderboards")
    op.drop_table("leaderboards")
