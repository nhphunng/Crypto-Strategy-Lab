from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from crypto_lab.application.sentiment.analyze_pending_news import AnalyzePendingNews
from crypto_lab.application.sentiment.errors import SentimentModelUnavailable
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel, SentimentStatus

PUBLISHED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
ANALYZED_AT = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def _item(index: int) -> NewsItem:
    published = PUBLISHED_AT + timedelta(minutes=index)
    return NewsItem(
        id=UUID(int=index),
        provider="cryptopanic",
        provider_item_id=f"article-{index}",
        title=f"Headline {index}",
        content=f"Content {index}",
        source="Example News",
        published_at=published,
        crawled_at=published + timedelta(minutes=5),
        related_coins=("BTC",),
        url=f"https://example.com/articles/{index}",
        canonical_url=f"https://example.com/articles/{index}",
    )


class FakeAnalyzer:
    model_id = "fake-model"
    model_version = "1.0.0"

    def __init__(self, *, fails_for: frozenset[UUID] = frozenset()) -> None:
        self.fails_for = fails_for
        self.calls: list[UUID] = []

    async def analyze(self, item: NewsItem) -> tuple[SentimentLabel, Decimal]:
        self.calls.append(item.id)
        if item.id in self.fails_for:
            raise RuntimeError("analyzer exploded")
        return SentimentLabel.POSITIVE, Decimal("0.5")


class FakeRepository:
    def __init__(self, pending: tuple[NewsItem, ...]) -> None:
        self.pending = pending
        self.saved: list[NewsSentimentAnalysis] = []
        self.list_pending_calls: list[tuple[ModelRef, int]] = []

    async def list_pending(self, model: ModelRef, limit: int) -> tuple[NewsItem, ...]:
        self.list_pending_calls.append((model, limit))
        return self.pending[:limit]

    async def save(self, analysis: NewsSentimentAnalysis) -> None:
        self.saved.append(analysis)

    async def latest_for(self, news_ids: tuple[UUID, ...]) -> dict[UUID, NewsSentimentAnalysis]:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_a_failing_item_does_not_stop_the_batch() -> None:
    items = (_item(1), _item(2), _item(3))
    failing_id = items[1].id
    analyzer = FakeAnalyzer(fails_for=frozenset({failing_id}))
    repository = FakeRepository(items)
    use_case = AnalyzePendingNews(
        analyzer=analyzer, repository=repository, clock=FixedClock(ANALYZED_AT)
    )

    report = await use_case.execute(limit=50)

    assert report.attempted == 3
    assert report.succeeded == 2
    assert report.failed == 1
    assert analyzer.calls == [item.id for item in items]
    assert len(repository.saved) == 3


@pytest.mark.asyncio
async def test_failing_item_is_saved_as_failed_with_a_failure_code() -> None:
    items = (_item(1),)
    analyzer = FakeAnalyzer(fails_for=frozenset({items[0].id}))
    repository = FakeRepository(items)
    use_case = AnalyzePendingNews(
        analyzer=analyzer, repository=repository, clock=FixedClock(ANALYZED_AT)
    )

    await use_case.execute()

    (saved,) = repository.saved
    assert saved.status is SentimentStatus.FAILED
    assert saved.failure_code == "RuntimeError"
    assert saved.label is SentimentLabel.NEUTRAL
    assert saved.score == Decimal("0")


@pytest.mark.asyncio
async def test_successful_items_are_saved_as_completed() -> None:
    items = (_item(1), _item(2))
    analyzer = FakeAnalyzer()
    repository = FakeRepository(items)
    use_case = AnalyzePendingNews(
        analyzer=analyzer, repository=repository, clock=FixedClock(ANALYZED_AT)
    )

    report = await use_case.execute()

    assert report.succeeded == 2
    assert report.failed == 0
    assert all(analysis.status is SentimentStatus.COMPLETED for analysis in repository.saved)
    assert all(analysis.label is SentimentLabel.POSITIVE for analysis in repository.saved)


@pytest.mark.asyncio
async def test_list_pending_is_queried_with_the_analyzers_exact_model_identity() -> None:
    analyzer = FakeAnalyzer()
    repository = FakeRepository(())
    use_case = AnalyzePendingNews(
        analyzer=analyzer, repository=repository, clock=FixedClock(ANALYZED_AT)
    )

    await use_case.execute(limit=25)

    (model, limit) = repository.list_pending_calls[0]
    assert model == ModelRef(analyzer.model_id, analyzer.model_version)
    assert limit == 25


async def test_model_load_failure_leaves_news_pending_for_retry() -> None:
    class UnavailableAnalyzer(FakeAnalyzer):
        async def analyze(self, item: NewsItem) -> tuple[SentimentLabel, Decimal]:
            raise SentimentModelUnavailable("offline")

    repository = FakeRepository((_item(1), _item(2)))
    service = AnalyzePendingNews(
        analyzer=UnavailableAnalyzer(), repository=repository, clock=FixedClock(ANALYZED_AT)
    )
    with pytest.raises(SentimentModelUnavailable):
        await service.execute()
    assert repository.saved == []
