"""Resilient background sentiment-analysis loop.

Runs one analysis batch immediately on start, then every ``interval_seconds``.
An analyzer or persistence failure for one cycle must not prevent a later
cycle, and the loop must stop cleanly on shutdown without leaking an async
task. Mirrors ``application.news.collection_loop.NewsCollectionLoop`` exactly.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from crypto_lab.application.sentiment.analyze_pending_news import AnalyzePendingNews

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SentimentAnalysisLoop:
    """Analyzes pending News at a fixed interval, isolating each cycle's failures."""

    analyze_pending_news: AnalyzePendingNews
    interval_seconds: float = 900.0
    batch_size: int = 50
    _task: asyncio.Task[None] | None = field(default=None, init=False)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):  # pragma: no cover - shutdown path
            pass

    async def _run(self) -> None:
        while True:
            try:
                report = await self.analyze_pending_news.execute(limit=self.batch_size)
                logger.info(
                    "sentiment_analysis_cycle_completed",
                    extra={
                        "fields": {
                            "attempted": report.attempted,
                            "succeeded": report.succeeded,
                            "failed": report.failed,
                        }
                    },
                )
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception:  # one bad cycle must not kill the loop
                logger.warning("sentiment_analysis_cycle_failed", exc_info=False)
            await asyncio.sleep(self.interval_seconds)


__all__ = ["SentimentAnalysisLoop"]
