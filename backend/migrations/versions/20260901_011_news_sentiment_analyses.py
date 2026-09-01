"""Create immutable, versioned news sentiment analyses.

Revision ID: 20260901_011_news_sentiment
Revises: 20260831_010_strategy_search
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260901_011_news_sentiment"
down_revision: str | None = "20260831_010_strategy_search"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_sentiment_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "news_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("news_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Numeric(7, 6), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_fingerprint", sa.CHAR(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_news_sentiment_analyses"),
        sa.UniqueConstraint(
            "news_id",
            "model_id",
            "model_version",
            "content_fingerprint",
            name="uq_news_sentiment_analyses_identity",
        ),
        sa.CheckConstraint(
            "status IN ('COMPLETED','FAILED')",
            name="ck_news_sentiment_analyses_status",
        ),
        sa.CheckConstraint(
            "label IN ('POSITIVE','NEUTRAL','NEGATIVE')",
            name="ck_news_sentiment_analyses_label",
        ),
    )
    op.create_index(
        "ix_news_sentiment_analyses_latest",
        "news_sentiment_analyses",
        ["news_id", "status", sa.text("analyzed_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_news_sentiment_analyses_pending_lookup",
        "news_sentiment_analyses",
        ["news_id", "model_id", "model_version", "content_fingerprint"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_news_sentiment_analyses_pending_lookup", table_name="news_sentiment_analyses")
    op.drop_index("ix_news_sentiment_analyses_latest", table_name="news_sentiment_analyses")
    op.drop_table("news_sentiment_analyses")
