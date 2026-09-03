"""Idempotent PostgreSQL adapter for the application news repository boundary."""

from __future__ import annotations

from dataclasses import replace

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.application.news.ports import NewsPage, NewsQuery, SentimentSummary, StoreNewsResult
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.infrastructure.persistence.news_models import NewsItemRow
from crypto_lab.infrastructure.persistence.sentiment_models import NewsSentimentAnalysisRow

# Mutable columns refreshed on an identity conflict with changed content. Identity
# (provider, provider_item_id), the row id, and published_at are never rewritten.
_MUTABLE_COLUMNS = (
    "title",
    "content",
    "source",
    "url",
    "canonical_url",
    "content_fingerprint",
    "related_coins",
    "crawled_at",
)


class SqlAlchemyNewsRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def upsert_many(
        self,
        items: tuple[NewsItem, ...],
    ) -> StoreNewsResult:
        inserted = updated = unchanged = 0
        async with self._sessions() as session, session.begin():
            for item in items:
                existing_id = await session.scalar(
                    select(NewsItemRow.id).where(
                        NewsItemRow.provider == item.provider,
                        NewsItemRow.provider_item_id == item.provider_item_id,
                    )
                )
                if existing_id is not None:
                    # Same provider identity: refresh mutable fields when the content
                    # changed, otherwise keep the row untouched. Never touch the id,
                    # the provider identity, or published_at.
                    insert_stmt = insert(NewsItemRow).values(_item_values(item))
                    excluded = insert_stmt.excluded
                    returned_id = await session.scalar(
                        insert_stmt.on_conflict_do_update(
                            index_elements=["provider", "provider_item_id"],
                            set_={column: getattr(excluded, column) for column in _MUTABLE_COLUMNS},
                            where=NewsItemRow.content_fingerprint != excluded.content_fingerprint,
                        ).returning(NewsItemRow.id)
                    )
                    if returned_id is None:
                        unchanged += 1
                    else:
                        updated += 1
                    continue

                # No matching provider identity: inserting must not duplicate a
                # canonical URL owned by another provider, nor rewrite its source.
                result = await session.execute(
                    insert(NewsItemRow)
                    .values(_item_values(item))
                    .on_conflict_do_nothing(index_elements=["canonical_url"])
                )
                if result.rowcount == 1:
                    inserted += 1
                else:
                    unchanged += 1
        return StoreNewsResult(
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
        )

    async def list(self, query: NewsQuery) -> NewsPage:
        conditions = _query_conditions(query)
        page_size = max(query.page_size, 1)
        offset = (max(query.page, 1) - 1) * page_size
        async with self._sessions() as session:
            distribution = (
                select(_latest_label().label("label"))
                .select_from(NewsItemRow)
                .where(*_query_conditions(replace(query, sentiment=None)))
                .subquery()
            )
            count_rows = (
                await session.execute(
                    select(distribution.c.label, func.count()).group_by(distribution.c.label)
                )
            ).all()
            counts: dict[str | None, int] = {label: count for label, count in count_rows}
            total = await session.scalar(
                select(func.count()).select_from(NewsItemRow).where(*conditions)
            )
            rows = (
                await session.scalars(
                    select(NewsItemRow)
                    .where(*conditions)
                    .order_by(NewsItemRow.published_at.desc(), NewsItemRow.id.asc())
                    .limit(page_size)
                    .offset(offset)
                )
            ).all()
        return NewsPage(
            items=tuple(_to_domain(row) for row in rows),
            page=query.page,
            page_size=query.page_size,
            total=int(total or 0),
            sentiment_summary=SentimentSummary(
                positive=counts.get("POSITIVE", 0),
                neutral=counts.get("NEUTRAL", 0),
                negative=counts.get("NEGATIVE", 0),
                pending=counts.get(None, 0),
            ),
        )


def _latest_label() -> ColumnElement[str]:
    analysis = NewsSentimentAnalysisRow
    return (
        select(analysis.label)
        .where(
            analysis.news_id == NewsItemRow.id,
            analysis.content_fingerprint == NewsItemRow.content_fingerprint,
            analysis.status == "COMPLETED",
        )
        .order_by(analysis.analyzed_at.desc(), analysis.id.desc())
        .limit(1)
        .correlate(NewsItemRow)
        .scalar_subquery()
    )


def _query_conditions(query: NewsQuery) -> tuple[ColumnElement[bool], ...]:
    conditions: list[ColumnElement[bool]] = []
    if query.coin:
        conditions.append(NewsItemRow.related_coins.any(query.coin))  # type: ignore[arg-type]
    if query.sentiment:
        conditions.append(_latest_label() == query.sentiment)
    if query.published_after is not None:
        conditions.append(NewsItemRow.published_at >= query.published_after)
    if query.published_before is not None:
        conditions.append(NewsItemRow.published_at < query.published_before)
    return tuple(conditions)


def _item_values(item: NewsItem) -> dict[str, object]:
    return {
        "id": item.id,
        "provider": item.provider,
        "provider_item_id": item.provider_item_id,
        "title": item.title,
        "content": item.content,
        "source": item.source,
        "published_at": item.published_at,
        "crawled_at": item.crawled_at,
        "related_coins": list(item.related_coins),
        "url": item.url,
        "canonical_url": item.canonical_url,
        "content_fingerprint": item.content_fingerprint,
    }


def _to_domain(row: NewsItemRow) -> NewsItem:
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
