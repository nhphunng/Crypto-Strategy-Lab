"""REST contract for GET /api/v1/news projecting real Sentiment analyses.

Mirrors test_news_api.py's style (a stub container over fakes, no real DB).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from crypto_lab.application.news.list_news import ListNews
from crypto_lab.application.news.ports import NewsPage, NewsQuery
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import SentimentLabel, SentimentStatus
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
ANALYZED_AT = datetime(2026, 8, 30, 11, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class FakeNewsRepository:
    def __init__(self, items: tuple[NewsItem, ...]) -> None:
        self.items = items

    async def list(self, query: NewsQuery) -> NewsPage:
        start = (query.page - 1) * query.page_size
        return NewsPage(
            items=self.items[start : start + query.page_size],
            page=query.page,
            page_size=query.page_size,
            total=len(self.items),
        )


class FakeSentimentRepository:
    def __init__(self, analyses: Mapping[UUID, NewsSentimentAnalysis]) -> None:
        self.analyses = analyses
        self.requested: tuple[UUID, ...] | None = None

    async def latest_for(self, news_ids: tuple[UUID, ...]) -> Mapping[UUID, NewsSentimentAnalysis]:
        self.requested = news_ids
        return {news_id: self.analyses[news_id] for news_id in news_ids if news_id in self.analyses}


class StubContainer:
    def __init__(
        self,
        list_news: ListNews,
        sentiment_repository: FakeSentimentRepository | None = None,
    ) -> None:
        self.settings = Settings(_env_file=None)
        self.list_news = list_news
        self.sentiment_repository = sentiment_repository


def _news_item(index: int) -> NewsItem:
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
        related_coins=("BTC",),
        url=f"https://example.com/articles/{index}",
        canonical_url=f"https://example.com/articles/{index}",
    )


def _client(
    items: tuple[NewsItem, ...],
    analyses: Mapping[UUID, NewsSentimentAnalysis] = {},
) -> AsyncClient:
    app = create_app(
        StubContainer(
            ListNews(FakeNewsRepository(items), FixedClock(NOW)),
            FakeSentimentRepository(analyses),
        )
    )
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_pending_item_with_no_analysis_projects_null_sentiment() -> None:
    item = _news_item(1)
    client = _client((item,), {})

    response = await client.get("/api/v1/news")

    assert response.json()["data"]["items"][0]["sentiment"] is None


async def test_item_whose_only_analysis_failed_projects_null_sentiment() -> None:
    item = _news_item(1)
    failed = NewsSentimentAnalysis(
        news_id=item.id,
        model_id="lexicon-sentiment",
        model_version="1.0.0",
        label=SentimentLabel.NEUTRAL,
        score=Decimal("0"),
        analyzed_at=ANALYZED_AT,
        content_fingerprint=item.content_fingerprint,
        status=SentimentStatus.FAILED,
        failure_code="TimeoutError",
    )
    client = _client((item,), {item.id: failed})

    response = await client.get("/api/v1/news")

    assert response.json()["data"]["items"][0]["sentiment"] is None


async def test_item_with_a_completed_analysis_projects_a_real_sentiment_payload() -> None:
    item = _news_item(1)
    completed = NewsSentimentAnalysis(
        news_id=item.id,
        model_id="lexicon-sentiment",
        model_version="1.0.0",
        label=SentimentLabel.POSITIVE,
        score=Decimal("0.842000"),
        analyzed_at=ANALYZED_AT,
        content_fingerprint=item.content_fingerprint,
        status=SentimentStatus.COMPLETED,
    )
    client = _client((item,), {item.id: completed})

    response = await client.get("/api/v1/news")

    sentiment = response.json()["data"]["items"][0]["sentiment"]
    assert sentiment is not None
    assert sentiment["label"] == "POSITIVE"
    assert Decimal(sentiment["score"]) == Decimal("0.842000")
    assert sentiment["modelId"] == "lexicon-sentiment"
    assert sentiment["modelVersion"] == "1.0.0"


async def test_missing_sentiment_repository_still_serves_news_with_null_sentiment() -> None:
    item = _news_item(1)
    app = create_app(StubContainer(ListNews(FakeNewsRepository((item,)), FixedClock(NOW))))
    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    response = await client.get("/api/v1/news")

    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["sentiment"] is None
