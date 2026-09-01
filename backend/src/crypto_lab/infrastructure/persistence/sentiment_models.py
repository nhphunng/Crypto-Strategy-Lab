from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class NewsSentimentAnalysisRow(Base):
    __tablename__ = "news_sentiment_analyses"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    news_id: Mapped[UUID] = mapped_column(
        ForeignKey("news_items.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(7, 6), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "news_id",
            "model_id",
            "model_version",
            "content_fingerprint",
            name="uq_news_sentiment_analyses_identity",
        ),
        Index(
            "ix_news_sentiment_analyses_latest",
            "news_id",
            "status",
            analyzed_at.desc(),
        ),
        Index(
            "ix_news_sentiment_analyses_pending_lookup",
            "news_id",
            "model_id",
            "model_version",
            "content_fingerprint",
        ),
    )
