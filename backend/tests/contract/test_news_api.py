"""REST contract for GET /api/v1/news, filters, pagination, and error envelopes."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from crypto_lab.application.news.list_news import ListNews
from crypto_lab.application.news.ports import NewsPage, NewsQuery
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class FakeNewsRepository:
    def __init__(self, items: tuple[NewsItem, ...]) -> None:
        self.items = items
        self.queries: list[NewsQuery] = []

    async def list(self, query: NewsQuery) -> NewsPage:
        self.queries.append(query)
        start = (query.page - 1) * query.page_size
        return NewsPage(
            items=self.items[start : start + query.page_size],
            page=query.page,
            page_size=query.page_size,
            total=len(self.items),
        )


class StubContainer:
    def __init__(self, list_news: ListNews) -> None:
        self.settings = Settings(_env_file=None)
        self.list_news = list_news


def _news_item(index: int, *, coin: str = "BTC") -> NewsItem:
    published = NOW - timedelta(hours=index)
    return NewsItem(
        id=UUID(int=index),
        provider="cryptopanic",
        provider_item_id=f"article-{index}",
        title=f"Bitcoin headline {index}",
        content=f"Full content {index}",
        source="Example News",
        published_at=published,
        crawled_at=published + timedelta(minutes=5),
        related_coins=(coin,),
        url=f"https://example.com/articles/{index}",
        canonical_url=f"https://example.com/articles/{index}",
    )


def _client(items: tuple[NewsItem, ...] = ()) -> tuple[AsyncClient, FakeNewsRepository]:
    repository = FakeNewsRepository(items)
    app = create_app(StubContainer(ListNews(repository, FixedClock(NOW))))
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    return client, repository


async def test_list_news_returns_stable_camel_case_envelope() -> None:
    client, _ = _client((_news_item(1),))
    response = await client.get("/api/v1/news", headers={"X-Request-ID": "req-news"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "News loaded."
    assert body["requestId"] == "req-news"
    assert INSTANT.fullmatch(body["timestamp"])
    data = body["data"]
    assert data["page"] == 1
    assert data["pageSize"] == 50
    assert data["total"] == 1
    item = data["items"][0]
    for field in (
        "newsId",
        "title",
        "content",
        "source",
        "publishedAt",
        "crawledAt",
        "relatedCoins",
        "url",
        "sentiment",
    ):
        assert field in item


async def test_empty_page_returns_200_with_empty_items() -> None:
    client, _ = _client(())
    response = await client.get("/api/v1/news")

    assert response.status_code == 200
    assert response.json()["data"]["items"] == []
    assert response.json()["data"]["total"] == 0


async def test_response_exposes_no_internal_fields() -> None:
    client, _ = _client((_news_item(1),))
    data = (await client.get("/api/v1/news")).json()["data"]
    item = data["items"][0]

    for internal in ("provider", "providerItemId", "canonicalUrl", "contentFingerprint"):
        assert internal not in item
    assert isinstance(item["crawledAt"], str)  # crawledAt IS part of the public contract
    assert set(item.keys()) == {
        "newsId",
        "title",
        "content",
        "source",
        "publishedAt",
        "crawledAt",
        "relatedCoins",
        "url",
        "sentiment",
    }


async def test_sentiment_is_exactly_null_for_task_three() -> None:
    client, _ = _client((_news_item(1),))
    item = (await client.get("/api/v1/news")).json()["data"]["items"][0]

    assert item["sentiment"] is None


async def test_default_window_and_pagination_reach_the_repository() -> None:
    client, repository = _client((_news_item(1),))
    await client.get("/api/v1/news")

    query = repository.queries[0]
    assert query.published_after == NOW - timedelta(days=7)
    assert query.published_before == NOW
    assert query.page == 1
    assert query.page_size == 50


async def test_supplied_filters_are_forwarded_in_camel_case() -> None:
    client, repository = _client((_news_item(1),))
    await client.get(
        "/api/v1/news",
        params={
            "coin": "BTC",
            "publishedAfter": "2026-08-23T00:00:00Z",
            "publishedBefore": "2026-08-31T00:00:00Z",
            "page": 2,
            "pageSize": 25,
        },
    )

    query = repository.queries[0]
    assert query.coin == "BTC"
    assert query.published_after == datetime(2026, 8, 23, tzinfo=UTC)
    assert query.published_before == datetime(2026, 8, 31, tzinfo=UTC)
    assert query.page == 2
    assert query.page_size == 25


@pytest.mark.parametrize("coin", ("btc", "BT C", "123BTC!"))
async def test_invalid_coin_returns_stable_news_coin_invalid(coin: str) -> None:
    client, _ = _client(())
    response = await client.get("/api/v1/news", params={"coin": coin})
    body = response.json()

    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "NEWS_COIN_INVALID"
    assert body["error"]["retryable"] is False


async def test_invalid_published_after_returns_stable_news_range_invalid() -> None:
    client, _ = _client(())
    response = await client.get("/api/v1/news", params={"publishedAfter": "not-a-date"})
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "NEWS_RANGE_INVALID"


async def test_inverted_range_returns_stable_news_range_invalid() -> None:
    client, _ = _client(())
    response = await client.get(
        "/api/v1/news",
        params={
            "publishedAfter": "2026-08-31T00:00:00Z",
            "publishedBefore": "2026-08-23T00:00:00Z",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NEWS_RANGE_INVALID"


@pytest.mark.parametrize("params", ({"page": 0}, {"pageSize": 0}, {"pageSize": 101}, {"page": -1}))
async def test_invalid_page_returns_stable_news_page_invalid(params: dict[str, int]) -> None:
    client, _ = _client(())
    response = await client.get("/api/v1/news", params=params)
    body = response.json()

    assert response.status_code == 422
    assert body["error"]["code"] == "NEWS_PAGE_INVALID"


@pytest.mark.parametrize("params", ({"page": 1, "pageSize": 100}, {"pageSize": 1}))
async def test_page_boundaries_are_accepted(params: dict[str, int]) -> None:
    client, _ = _client((_news_item(1),))
    response = await client.get("/api/v1/news", params=params)

    assert response.status_code == 200
    assert response.json()["data"]["pageSize"] == params.get("pageSize", 50)
