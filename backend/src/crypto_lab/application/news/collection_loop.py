"""Resilient background news collection loop.

Runs one collection cycle immediately on start, then every ``interval_seconds``.
A provider or transport failure must not prevent a later cycle, and the loop must
stop cleanly on shutdown without leaking an async task.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from crypto_lab.application.news.collect_news import CollectNews

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NewsCollectionLoop:
    """Collects news at a fixed interval, isolating each cycle's failures."""

    collect_news: CollectNews
    interval_seconds: float = 900.0
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
                result = await self.collect_news.execute()
                logger.info(
                    "news_collection_cycle_completed",
                    extra={
                        "fields": {
                            "inserted": result.inserted,
                            "updated": result.updated,
                            "unchanged": result.unchanged,
                        }
                    },
                )
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception:  # one bad cycle must not kill the loop
                logger.warning("news_collection_cycle_failed", exc_info=False)
            await asyncio.sleep(self.interval_seconds)


__all__ = ["NewsCollectionLoop"]
