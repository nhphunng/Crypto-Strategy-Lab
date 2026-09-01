"""Ports for the Sentiment Service.

The Sentiment Service only ever *consumes* already-stored News: nothing here is
ever invoked from the crawler/collector, and nothing here writes back to
``news_items``. See ``domain.sentiment.analysis`` for the immutability and
identity rules a ``SentimentAnalysisRepository`` implementation must uphold.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel


class SentimentAnalyzer(Protocol):
    """A versioned model that scores one News item's sentiment.

    Implementations must not raise for ordinary input; a raised exception is
    treated by ``AnalyzePendingNews`` as an analysis failure for that item
    only (failure isolation) and is recorded as a FAILED analysis row rather
    than propagated.
    """

    model_id: str
    model_version: str

    async def analyze(self, item: NewsItem) -> tuple[SentimentLabel, Decimal]: ...


class SentimentAnalysisRepository(Protocol):
    async def list_pending(self, model: ModelRef, limit: int) -> tuple[NewsItem, ...]: ...

    async def save(self, analysis: NewsSentimentAnalysis) -> None: ...

    async def latest_for(
        self, news_ids: tuple[UUID, ...]
    ) -> Mapping[UUID, NewsSentimentAnalysis]: ...


__all__ = ["SentimentAnalysisRepository", "SentimentAnalyzer"]
