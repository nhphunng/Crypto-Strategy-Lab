from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from crypto_lab.application.news.list_news import ListNews
from crypto_lab.application.news.ports import NewsPage, NewsQuery
from crypto_lab.domain.news.item import NewsItem

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class FakeRepository:
    def __init__(self, page: NewsPage) -> None:
        self.page = page
        self.queries: list[NewsQuery] = []

    async def list(self, query: NewsQuery) -> NewsPage:
        self.queries.append(query)
        return self.page


def _news_item() -> NewsItem:
    return NewsItem(
        id=UUID(int=1),
        provider="cryptopanic",
        provider_item_id="article-1",
        title="Bitcoin reaches a new high",
        content="Bitcoin moved above its prior high.",
        source="Example News",
        published_at=NOW - timedelta(hours=1),
        crawled_at=NOW,
        related_coins=("BTC",),
        url="https://example.com/articles/1",
        canonical_url="https://example.com/articles/1",
    )


@pytest.mark.asyncio
async def test_list_news_applies_default_window_and_pagination() -> None:
    page = NewsPage(items=(_news_item(),), page=1, page_size=50, total=1)
    repository = FakeRepository(page)
    service = ListNews(repository, FakeClock(NOW))

    result = await service.execute(NewsQuery())

    assert result == page
    recorded = repository.queries[0]
    assert recorded.published_after == NOW - timedelta(days=7)
    assert recorded.published_before == NOW
    assert recorded.page == 1
    assert recorded.page_size == 50


@pytest.mark.asyncio
async def test_list_news_preserves_explicit_filters_and_paging() -> None:
    page = NewsPage(items=(), page=2, page_size=25, total=40)
    repository = FakeRepository(page)
    service = ListNews(repository, FakeClock(NOW))

    await service.execute(
        NewsQuery(
            coin="BTC",
            published_after=NOW - timedelta(days=3),
            published_before=NOW - timedelta(days=1),
            page=2,
            page_size=25,
        )
    )

    recorded = repository.queries[0]
    assert recorded.coin == "BTC"
    assert recorded.published_after == NOW - timedelta(days=3)
    assert recorded.published_before == NOW - timedelta(days=1)
    assert recorded.page == 2
    assert recorded.page_size == 25
