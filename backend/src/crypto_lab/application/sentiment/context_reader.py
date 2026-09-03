"""Read-only sentiment series for a pair over a time window, for strategies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from crypto_lab.domain.sentiment.model import ModelRef


@dataclass(frozen=True, slots=True)
class SentimentDataPoint:
    published_at: datetime
    analyzed_at: datetime
    signed_score: Decimal  # already in [-1, 1]; sign encodes label direction
    news_id: str | None = None
    analysis_id: str | None = None
    content_fingerprint: str | None = None


class SentimentContextReader(Protocol):
    async def series(
        self,
        pair: str,
        start_time: datetime,
        end_time: datetime,
        model: ModelRef,
    ) -> tuple[SentimentDataPoint, ...]: ...


__all__ = ["SentimentContextReader", "SentimentDataPoint"]
