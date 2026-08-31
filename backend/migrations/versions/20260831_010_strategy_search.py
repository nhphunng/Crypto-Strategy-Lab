"""Create durable strategy search runs and candidates.

Revision ID: 20260831_010_strategy_search
Revises: 20260828_009_strategy_configs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260831_010_strategy_search"
down_revision: str | None = "20260830_010_news"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_search_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candle_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("strategy_ids", postgresql.JSONB(), nullable=False),
        sa.Column("minimum_size", sa.Integer(), nullable=False),
        sa.Column("maximum_size", sa.Integer(), nullable=False),
        sa.Column("candidate_limit", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("no_improvement_limit", sa.Integer(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("generator_id", sa.String(64), nullable=False),
        sa.Column("generator_version", sa.String(32), nullable=False),
        sa.Column("generated", sa.Integer(), nullable=False),
        sa.Column("running", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("top_score", sa.Numeric(20, 8)),
        sa.Column("top_candidate", sa.String(512)),
        sa.Column("current_candidate", sa.String(512)),
        sa.Column("stop_reason", sa.String(64)),
        sa.Column("failure_detail", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')",
            name="ck_strategy_search_runs_status",
        ),
    )
    op.create_index("ix_strategy_search_runs_created", "strategy_search_runs", ["created_at"])
    op.create_table(
        "strategy_search_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "search_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_search_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(512), nullable=False),
        sa.Column("members", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("score", sa.Numeric(20, 8)),
        sa.Column(
            "backtest_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("backtest_runs.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "evaluation_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_results.id", ondelete="SET NULL"),
        ),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "search_run_id", "fingerprint", name="uq_strategy_search_candidate_fingerprint"
        ),
    )
    op.create_index(
        "ix_strategy_search_candidates_run_score",
        "strategy_search_candidates",
        ["search_run_id", "score"],
    )


def downgrade() -> None:
    op.drop_table("strategy_search_candidates")
    op.drop_table("strategy_search_runs")
