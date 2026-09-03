from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel, SentimentStatus
from crypto_lab.infrastructure.persistence.repositories.news_repository import (
    SqlAlchemyNewsRepository,
)
from crypto_lab.infrastructure.persistence.repositories.sentiment_repository import (
    SqlAlchemySentimentAnalysisRepository,
)

pytestmark = pytest.mark.integration

PUBLISHED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
ANALYZED_AT = datetime(2026, 8, 29, 11, 0, tzinfo=UTC)
MODEL = ModelRef("lexicon-sentiment", "1.0.0")


def _make_item(**overrides: object) -> NewsItem:
    values: dict[str, object] = {
        "id": UUID(int=1),
        "provider": "cryptopanic",
        "provider_item_id": "article-1",
        "title": "Bitcoin reaches a new high",
        "content": "Bitcoin moved above its prior high.",
        "source": "Example News",
        "published_at": PUBLISHED_AT,
        "crawled_at": PUBLISHED_AT + timedelta(minutes=5),
        "related_coins": ("BTC",),
        "url": "https://example.com/articles/1",
        "canonical_url": "https://example.com/articles/1",
    }
    values.update(overrides)
    return NewsItem(**values)  # type: ignore[arg-type]


def _completed(item: NewsItem, **overrides: object) -> NewsSentimentAnalysis:
    values: dict[str, object] = {
        "news_id": item.id,
        "model_id": MODEL.model_id,
        "model_version": MODEL.model_version,
        "label": SentimentLabel.POSITIVE,
        "score": Decimal("0.5"),
        "analyzed_at": ANALYZED_AT,
        "content_fingerprint": item.content_fingerprint,
        "status": SentimentStatus.COMPLETED,
    }
    values.update(overrides)
    return NewsSentimentAnalysis(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_list_pending_excludes_items_already_analyzed_at_current_fingerprint(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    item = _make_item()
    await news_repository.upsert_many((item,))
    await sentiment_repository.save(_completed(item))

    pending = await sentiment_repository.list_pending(MODEL, limit=50)

    assert pending == ()


@pytest.mark.asyncio
async def test_list_pending_includes_unanalyzed_items(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    item = _make_item()
    await news_repository.upsert_many((item,))

    pending = await sentiment_repository.list_pending(MODEL, limit=50)

    assert [entry.id for entry in pending] == [item.id]


@pytest.mark.asyncio
async def test_list_pending_includes_items_whose_content_changed_since_a_stale_analysis(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    original = _make_item()
    await news_repository.upsert_many((original,))
    await sentiment_repository.save(_completed(original))

    revised = _make_item(title="Bitcoin dips instead", content="Bitcoin traded lower.")
    await news_repository.upsert_many((revised,))

    pending = await sentiment_repository.list_pending(MODEL, limit=50)

    assert [entry.id for entry in pending] == [original.id]
    assert pending[0].content_fingerprint == revised.content_fingerprint


@pytest.mark.asyncio
async def test_list_pending_excludes_items_analyzed_under_a_different_model(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    item = _make_item()
    await news_repository.upsert_many((item,))
    await sentiment_repository.save(_completed(item))

    other_model = ModelRef("other-model", "9.9.9")
    pending = await sentiment_repository.list_pending(other_model, limit=50)

    assert [entry.id for entry in pending] == [item.id]


@pytest.mark.asyncio
async def test_save_twice_with_identical_identity_is_idempotent_no_duplicate_no_error(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    item = _make_item()
    await news_repository.upsert_many((item,))
    analysis = _completed(item)

    await sentiment_repository.save(analysis)
    await sentiment_repository.save(analysis)

    latest = await sentiment_repository.latest_for((item.id,))
    assert set(latest) == {item.id}


@pytest.mark.asyncio
async def test_latest_for_returns_only_completed_rows(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    failed_item = _make_item()
    await news_repository.upsert_many((failed_item,))
    await sentiment_repository.save(
        NewsSentimentAnalysis(
            news_id=failed_item.id,
            model_id=MODEL.model_id,
            model_version=MODEL.model_version,
            label=SentimentLabel.NEUTRAL,
            score=Decimal("0"),
            analyzed_at=ANALYZED_AT,
            content_fingerprint=failed_item.content_fingerprint,
            status=SentimentStatus.FAILED,
            failure_code="TimeoutError",
        )
    )

    latest = await sentiment_repository.latest_for((failed_item.id,))

    assert latest == {}


@pytest.mark.asyncio
async def test_latest_for_returns_newest_analyzed_at_per_news_id(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    item = _make_item()
    await news_repository.upsert_many((item,))
    older = _completed(
        item,
        label=SentimentLabel.NEGATIVE,
        score=Decimal("0.9"),
        analyzed_at=ANALYZED_AT,
        content_fingerprint="a" * 64,
    )
    newer = _completed(
        item,
        label=SentimentLabel.POSITIVE,
        score=Decimal("0.4"),
        analyzed_at=ANALYZED_AT + timedelta(hours=1),
        content_fingerprint=item.content_fingerprint,
    )
    await sentiment_repository.save(older)
    await sentiment_repository.save(newer)

    latest = await sentiment_repository.latest_for((item.id,))

    assert latest[item.id].label is SentimentLabel.POSITIVE
    assert latest[item.id].analyzed_at == newer.analyzed_at


@pytest.mark.asyncio
async def test_count_by_status_reports_pending_analyzed_and_failed(
    sentiment_fixture: tuple[SqlAlchemyNewsRepository, SqlAlchemySentimentAnalysisRepository],
) -> None:
    news_repository, sentiment_repository = sentiment_fixture
    completed_item = _make_item()
    failed_item = _make_item(
        id=UUID(int=2),
        provider_item_id="article-2",
        url="https://example.com/2",
        canonical_url="https://example.com/2",
    )
    pending_item = _make_item(
        id=UUID(int=3),
        provider_item_id="article-3",
        url="https://example.com/3",
        canonical_url="https://example.com/3",
    )
    await news_repository.upsert_many((completed_item, failed_item, pending_item))
    await sentiment_repository.save(_completed(completed_item))
    await sentiment_repository.save(
        NewsSentimentAnalysis(
            news_id=failed_item.id,
            model_id=MODEL.model_id,
            model_version=MODEL.model_version,
            label=SentimentLabel.NEUTRAL,
            score=Decimal("0"),
            analyzed_at=ANALYZED_AT,
            content_fingerprint=failed_item.content_fingerprint,
            status=SentimentStatus.FAILED,
            failure_code="TimeoutError",
        )
    )

    counts = await sentiment_repository.count_by_status(MODEL)

    # completed_item and failed_item both have a row at their current
    # fingerprint (so neither is "pending" -- a FAILED row still counts as
    # attempted); only pending_item has no row at all.
    assert counts == {"pending": 1, "analyzed": 1, "failed": 1}
