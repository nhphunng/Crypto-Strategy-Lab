"""Create persisted cryptocurrency news items.

Revision ID: 20260830_010_news
Revises: 20260828_009_strategy_configs
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_010_news"
down_revision: str | None = "20260828_009_strategy_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_item_id", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("related_coins", postgresql.ARRAY(sa.String(length=16)), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.CHAR(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_news_items"),
        sa.UniqueConstraint(
            "provider",
            "provider_item_id",
            name="uq_news_items_provider_item",
        ),
        sa.UniqueConstraint("canonical_url", name="uq_news_items_canonical_url"),
    )
    op.create_index(
        "ix_news_items_related_coins",
        "news_items",
        ["related_coins"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_news_items_published",
        "news_items",
        [sa.text("published_at DESC"), "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_news_items_published", table_name="news_items")
    op.drop_index("ix_news_items_related_coins", table_name="news_items")
    op.drop_table("news_items")
