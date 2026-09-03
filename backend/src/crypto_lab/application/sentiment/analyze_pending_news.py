"""Run the configured Sentiment Analyzer over already-stored, unanalyzed News.

This use case never touches the crawler/collector: it only reads News items
the repository reports as pending for the given model, and only ever writes
new ``NewsSentimentAnalysis`` rows (never News rows). A failure analyzing one
item is isolated to that item -- it is recorded as a FAILED analysis and the
batch continues, so a model failure never makes already-stored News, Market,
or Backtest features unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from crypto_lab.application.market_data.ports import Clock
from crypto_lab.application.sentiment.errors import SentimentModelUnavailable
from crypto_lab.application.sentiment.ports import SentimentAnalysisRepository, SentimentAnalyzer
from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel, SentimentStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SentimentBatchReport:
    attempted: int
    succeeded: int
    failed: int


class AnalyzePendingNews:
    def __init__(
        self,
        *,
        analyzer: SentimentAnalyzer,
        repository: SentimentAnalysisRepository,
        clock: Clock,
    ) -> None:
        self._analyzer = analyzer
        self._repository = repository
        self._clock = clock

    async def execute(self, *, limit: int = 50) -> SentimentBatchReport:
        model = ModelRef(self._analyzer.model_id, self._analyzer.model_version)
        pending = await self._repository.list_pending(model, limit)
        succeeded = 0
        failed = 0
        for item in pending:
            try:
                label, score = await self._analyzer.analyze(item)
                analysis = NewsSentimentAnalysis(
                    news_id=item.id,
                    model_id=model.model_id,
                    model_version=model.model_version,
                    label=label,
                    score=score,
                    analyzed_at=self._clock.now(),
                    content_fingerprint=item.content_fingerprint,
                    status=SentimentStatus.COMPLETED,
                )
                await self._repository.save(analysis)
                succeeded += 1
            except SentimentModelUnavailable:
                # A missing model or temporary download failure is not bad news data.
                # Do not permanently mark the whole batch FAILED; retry next cycle.
                raise
            except Exception as exc:  # one bad item must not stop the batch
                logger.warning(
                    "sentiment_analysis_item_failed",
                    extra={
                        "fields": {
                            "news_id": str(item.id),
                            "reason": type(exc).__name__,
                        }
                    },
                )
                failure = NewsSentimentAnalysis(
                    news_id=item.id,
                    model_id=model.model_id,
                    model_version=model.model_version,
                    label=SentimentLabel.NEUTRAL,
                    score=Decimal("0"),
                    analyzed_at=self._clock.now(),
                    content_fingerprint=item.content_fingerprint,
                    status=SentimentStatus.FAILED,
                    failure_code=type(exc).__name__[:64],
                )
                await self._repository.save(failure)
                failed += 1
        return SentimentBatchReport(attempted=len(pending), succeeded=succeeded, failed=failed)


__all__ = ["AnalyzePendingNews", "SentimentBatchReport"]
