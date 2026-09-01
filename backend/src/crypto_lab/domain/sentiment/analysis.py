"""Immutable, versioned sentiment analysis of a stored News item.

Analyses are never mutated: a retry of the same model against the same content
must be idempotent (same deterministic id, no duplicate row), and a changed
model version or changed News content always produces a brand-new row rather
than rewriting history. This is enforced at the persistence boundary (an
INSERT ... ON CONFLICT DO NOTHING keyed by this identity); this module only
computes the identity and validates the value itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from crypto_lab.domain.market_data.timeframe import require_utc
from crypto_lab.domain.sentiment.model import SentimentLabel, SentimentStatus

SENTIMENT_NAMESPACE = uuid5(NAMESPACE_URL, "crypto-lab/news-sentiment/v1")


@dataclass(frozen=True, slots=True)
class NewsSentimentAnalysis:
    id: UUID = field(init=False)
    news_id: UUID
    model_id: str
    model_version: str
    label: SentimentLabel
    score: Decimal
    analyzed_at: datetime
    content_fingerprint: str
    status: SentimentStatus
    failure_code: str | None = None

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id must not be blank")
        if not self.model_version.strip():
            raise ValueError("model_version must not be blank")
        if not self.content_fingerprint.strip():
            raise ValueError("content_fingerprint must not be blank")
        analyzed_at = require_utc(self.analyzed_at)
        object.__setattr__(self, "analyzed_at", analyzed_at)
        if not self.score.is_finite():
            raise ValueError("score must be finite")
        if self.score < Decimal("0") or self.score > Decimal("1"):
            raise ValueError("score must be within [0, 1]")
        if self.status is SentimentStatus.COMPLETED and self.failure_code is not None:
            raise ValueError("a completed analysis must not carry a failure_code")
        if self.status is SentimentStatus.FAILED:
            if self.failure_code is None or not self.failure_code.strip():
                raise ValueError("a failed analysis requires a non-blank failure_code")
            # Convention: a failed analysis carries a neutral, zero-weight placeholder
            # label/score rather than a fabricated one; callers must gate on `status`.
            if self.label is not SentimentLabel.NEUTRAL or self.score != Decimal("0"):
                raise ValueError("a failed analysis must use the NEUTRAL/0 placeholder")
        object.__setattr__(
            self,
            "id",
            uuid5(
                SENTIMENT_NAMESPACE,
                f"{self.news_id}|{self.model_id}|{self.model_version}|{self.content_fingerprint}",
            ),
        )

    @property
    def signed_score(self) -> Decimal:
        """The score signed by label direction, for averaging across articles."""

        if self.status is SentimentStatus.FAILED:
            return Decimal("0")
        if self.label is SentimentLabel.POSITIVE:
            return self.score
        if self.label is SentimentLabel.NEGATIVE:
            return -self.score
        return Decimal("0")


__all__ = ["SENTIMENT_NAMESPACE", "NewsSentimentAnalysis"]
