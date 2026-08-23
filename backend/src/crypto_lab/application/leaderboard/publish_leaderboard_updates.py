"""Evaluation-completion ingestion and retry-safe publication of updates.

Publication happens only after the transaction holding the projection change
and its durable update record commits, so a failed publish can be retried
without repeating or rolling back the ranking change.
"""

from __future__ import annotations

import asyncio
import logging

from crypto_lab.application.leaderboard.ports import (
    Clock,
    LeaderboardRepository,
    LeaderboardUpdatePublisher,
    ProjectionOutcome,
)
from crypto_lab.application.leaderboard.update_leaderboard import UpdateLeaderboard

logger = logging.getLogger("crypto_lab.leaderboard.publisher")

DEFAULT_BATCH_SIZE = 50
DEFAULT_POLL_SECONDS = 0.25


class PublishLeaderboardUpdates:
    """Claim committed update records and deliver them at least once."""

    def __init__(
        self,
        repository: LeaderboardRepository,
        publisher: LeaderboardUpdatePublisher,
        clock: Clock,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._repository = repository
        self._publisher = publisher
        self._clock = clock
        self._batch_size = batch_size

    async def dispatch_once(self) -> int:
        pending = await self._repository.claim_pending_updates(self._batch_size)
        published = 0
        for item in pending:
            try:
                await self._publisher.publish(item.event)
            except Exception:  # pragma: no cover - transport failure is retried
                logger.warning(
                    "leaderboard_publish_failed",
                    extra={"fields": {"event_id": str(item.event.event_id)}},
                )
                continue
            await self._repository.mark_published(item.record_id, self._clock.now())
            published += 1
        return published


class LeaderboardIngestion:
    """Durable boundary invoked when an Evaluation Result becomes available."""

    def __init__(
        self,
        updater: UpdateLeaderboard,
        dispatcher: PublishLeaderboardUpdates,
    ) -> None:
        self._updater = updater
        self._dispatcher = dispatcher

    async def on_evaluation_completed(
        self,
        evaluation_result_id,
        *,
        request_id: str | None = None,
    ) -> tuple[ProjectionOutcome, ...]:
        outcomes = await self._updater.for_evaluation(evaluation_result_id, request_id=request_id)
        await self._dispatcher.dispatch_once()
        return outcomes


class UpdateDispatcherLoop:
    """Background poller so committed changes reach clients without a refresh."""

    def __init__(
        self,
        dispatcher: PublishLeaderboardUpdates,
        *,
        interval_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        self._dispatcher = dispatcher
        self._interval = interval_seconds
        self._task: asyncio.Task[None] | None = None

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
                await self._dispatcher.dispatch_once()
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                raise
            except Exception:
                logger.warning("leaderboard_dispatch_cycle_failed")
            await asyncio.sleep(self._interval)
