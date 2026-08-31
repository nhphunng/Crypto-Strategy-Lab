"""Record why a strategy-generation request failed.

Revision ID: 20260828_008_failure_reason
Revises: 20260824_007_integrity
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_008_failure_reason"
down_revision: str | None = "20260824_007_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "strategy_generation_requests",
        sa.Column("failure_category", sa.String(64), nullable=True),
    )
    op.add_column(
        "strategy_generation_requests",
        sa.Column("failure_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("strategy_generation_requests", "failure_message")
    op.drop_column("strategy_generation_requests", "failure_category")
