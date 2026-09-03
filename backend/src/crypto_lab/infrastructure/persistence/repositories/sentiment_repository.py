"""PostgreSQL adapter for the Sentiment Service's own read/write boundary.

This repository only ever reads ``news_items`` (never writes it) and only ever
writes ``news_sentiment_analyses`` as append-only, identity-keyed inserts --
see ``domain.sentiment.analysis`` for why analyses are immutable and
versioned. A separate, read-only query class (rather than extending the
existing ``NewsRepository`` Protocol/implementation) keeps that existing,
already-tested contract untouched.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel, SentimentStatus
from crypto_lab.infrastructure.persistence.news_models import NewsItemRow
from crypto_lab.infrastructure.persistence.sentiment_models import NewsSentimentAnalysisRow


class SqlAlchemySentimentAnalysisRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def list_pending(self, model: ModelRef, limit: int) -> tuple[NewsItem, ...]:
        # "Pending" means: no analysis row exists for this exact model version
        # against the item's *current* content_fingerprint. A changed
        # fingerprint (edited content) makes a previously-analyzed item
        # pending again, by design.
        already_analyzed = (
            select(NewsSentimentAnalysisRow.id)
            .where(
                NewsSentimentAnalysisRow.news_id == NewsItemRow.id,
                NewsSentimentAnalysisRow.model_id == model.model_id,
                NewsSentimentAnalysisRow.model_version == model.model_version,
                NewsSentimentAnalysisRow.content_fingerprint == NewsItemRow.content_fingerprint,
            )
            .correlate(NewsItemRow)
        )
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(NewsItemRow)
                    .where(~exists(already_analyzed))
                    .order_by(NewsItemRow.published_at.asc(), NewsItemRow.id.asc())
                    .limit(max(limit, 0))
                )
            ).all()
        return tuple(_item_from_row(row) for row in rows)

    async def save(self, analysis: NewsSentimentAnalysis) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(NewsSentimentAnalysisRow)
                .values(
                    id=analysis.id,
                    news_id=analysis.news_id,
                    model_id=analysis.model_id,
                    model_version=analysis.model_version,
                    label=analysis.label.value,
                    score=analysis.score,
                    analyzed_at=analysis.analyzed_at,
                    content_fingerprint=analysis.content_fingerprint,
                    status=analysis.status.value,
                    failure_code=analysis.failure_code,
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        "news_id",
                        "model_id",
                        "model_version",
                        "content_fingerprint",
                    ]
                )
            )

    async def latest_for(self, news_ids: tuple[UUID, ...]) -> Mapping[UUID, NewsSentimentAnalysis]:
        if not news_ids:
            return {}
        row = NewsSentimentAnalysisRow
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(row)
                    .join(NewsItemRow, NewsItemRow.id == row.news_id)
                    .distinct(row.news_id)
                    .where(
                        row.news_id.in_(news_ids),
                        row.status == SentimentStatus.COMPLETED.value,
                        row.content_fingerprint == NewsItemRow.content_fingerprint,
                    )
                    .order_by(row.news_id, row.analyzed_at.desc(), row.id.desc())
                )
            ).all()
        return {analysis.news_id: analysis for analysis in (_analysis_from_row(r) for r in rows)}

    async def count_by_status(self, model: ModelRef) -> Mapping[str, int]:
        row = NewsSentimentAnalysisRow
        async with self._sessions() as session:
            analyzed = await session.scalar(
                select(func.count())
                .select_from(row)
                .where(
                    row.model_id == model.model_id,
                    row.model_version == model.model_version,
                    row.status == SentimentStatus.COMPLETED.value,
                )
            )
            failed = await session.scalar(
                select(func.count())
                .select_from(row)
                .where(
                    row.model_id == model.model_id,
                    row.model_version == model.model_version,
                    row.status == SentimentStatus.FAILED.value,
                )
            )
            already_analyzed = (
                select(row.id)
                .where(
                    and_(
                        row.news_id == NewsItemRow.id,
                        row.model_id == model.model_id,
                        row.model_version == model.model_version,
                        row.content_fingerprint == NewsItemRow.content_fingerprint,
                    )
                )
                .correlate(NewsItemRow)
            )
            pending = await session.scalar(
                select(func.count()).select_from(NewsItemRow).where(~exists(already_analyzed))
            )
        return {
            "pending": int(pending or 0),
            "analyzed": int(analyzed or 0),
            "failed": int(failed or 0),
        }


def _item_from_row(row: NewsItemRow) -> NewsItem:
    return NewsItem(
        id=row.id,
        provider=row.provider,
        provider_item_id=row.provider_item_id,
        title=row.title,
        content=row.content,
        source=row.source,
        published_at=row.published_at,
        crawled_at=row.crawled_at,
        related_coins=tuple(row.related_coins),
        url=row.url,
        canonical_url=row.canonical_url,
    )


def _analysis_from_row(row: NewsSentimentAnalysisRow) -> NewsSentimentAnalysis:
    return NewsSentimentAnalysis(
        news_id=row.news_id,
        model_id=row.model_id,
        model_version=row.model_version,
        label=SentimentLabel(row.label),
        score=row.score,
        analyzed_at=row.analyzed_at,
        content_fingerprint=row.content_fingerprint,
        status=SentimentStatus(row.status),
        failure_code=row.failure_code,
    )


__all__ = ["SqlAlchemySentimentAnalysisRepository"]
