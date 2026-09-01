from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CHAR, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class NewsItemRow(Base):
    __tablename__ = "news_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_item_id: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    related_coins: Mapped[list[str]] = mapped_column(ARRAY(String(16)), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(CHAR(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_item_id",
            name="uq_news_items_provider_item",
        ),
        UniqueConstraint("canonical_url", name="uq_news_items_canonical_url"),
        Index(
            "ix_news_items_related_coins",
            related_coins,
            postgresql_using="gin",
        ),
        Index("ix_news_items_published", published_at.desc(), id),
    )
