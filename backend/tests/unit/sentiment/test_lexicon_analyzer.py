from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.model import SentimentLabel
from crypto_lab.infrastructure.sentiment.lexicon_analyzer import LexiconSentimentAnalyzer

PUBLISHED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)


def _item(title: str, content: str) -> NewsItem:
    return NewsItem(
        id=UUID(int=1),
        provider="cryptopanic",
        provider_item_id="article-1",
        title=title,
        content=content,
        source="Example News",
        published_at=PUBLISHED_AT,
        crawled_at=PUBLISHED_AT + timedelta(minutes=5),
        related_coins=("BTC",),
        url="https://example.com/articles/1",
        canonical_url="https://example.com/articles/1",
    )


@pytest.mark.asyncio
async def test_clearly_positive_headline_scores_positive() -> None:
    analyzer = LexiconSentimentAnalyzer()
    item = _item(
        "Bitcoin rallies to a record high",
        "Institutions adopt crypto as the market gains and inflows surge.",
    )

    label, score = await analyzer.analyze(item)

    assert label is SentimentLabel.POSITIVE
    assert score > 0


@pytest.mark.asyncio
async def test_clearly_negative_headline_scores_negative() -> None:
    analyzer = LexiconSentimentAnalyzer()
    item = _item(
        "Exchange hacked as exploit drains millions",
        "A lawsuit follows the crash and a wave of liquidations.",
    )

    label, score = await analyzer.analyze(item)

    assert label is SentimentLabel.NEGATIVE
    assert score > 0


@pytest.mark.asyncio
async def test_neutral_headline_with_no_lexicon_hits_scores_neutral_zero() -> None:
    analyzer = LexiconSentimentAnalyzer()
    item = _item(
        "Weekly market summary published",
        "The report covers trading volume across several exchanges this week.",
    )

    label, score = await analyzer.analyze(item)

    assert label is SentimentLabel.NEUTRAL
    assert score == 0


@pytest.mark.asyncio
async def test_analysis_is_deterministic_across_repeated_calls() -> None:
    analyzer = LexiconSentimentAnalyzer()
    item = _item(
        "Bitcoin rallies to a record high",
        "Institutions adopt crypto as the market gains and inflows surge.",
    )

    first = await analyzer.analyze(item)
    second = await analyzer.analyze(item)

    assert first == second


@pytest.mark.asyncio
async def test_model_identity_is_stable() -> None:
    analyzer = LexiconSentimentAnalyzer()
    assert analyzer.model_id == "lexicon-sentiment"
    assert analyzer.model_version == "1.0.0"
