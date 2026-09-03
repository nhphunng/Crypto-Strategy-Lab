"""Persist sentiment provenance and background search ownership.

Revision ID: 20260903_012_sentiment_search
Revises: 20260901_011_news_sentiment
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260903_012_sentiment_search"
down_revision = "20260901_011_news_sentiment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "backtest_runs",
        sa.Column(
            "sentiment_provenance",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "strategy_search_runs",
        sa.Column(
            "origin",
            sa.String(16),
            nullable=False,
            server_default="MANUAL",
        ),
    )
    op.add_column("strategy_search_runs", sa.Column("loop_key", sa.String(64)))
    op.add_column("strategy_search_runs", sa.Column("cycle_index", sa.Integer()))
    op.create_index(
        "ix_search_runs_loop_cycle", "strategy_search_runs", ["loop_key", "cycle_index"]
    )


def downgrade() -> None:
    # An explicit downgrade discards only the added provenance/worker metadata.
    op.drop_index("ix_search_runs_loop_cycle", table_name="strategy_search_runs")
    op.drop_column("strategy_search_runs", "cycle_index")
    op.drop_column("strategy_search_runs", "loop_key")
    op.drop_column("strategy_search_runs", "origin")
    op.drop_column("backtest_runs", "sentiment_provenance")
