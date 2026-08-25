"""Structured leaderboard log context and lightweight in-process metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from crypto_lab.application.leaderboard.ports import (
    LeaderboardUpdatedEvent,
    ProjectionOutcome,
    UpdateSource,
)

logger = logging.getLogger("crypto_lab.leaderboard")

ALLOWED_LOG_FIELDS = (
    "request_id",
    "run_id",
    "job_id",
    "leaderboard_id",
    "evaluation_result_id",
    "strategy_id",
    "strategy_version",
    "projection_version",
    "scope_key",
    "rank_metric",
    "k",
    "entry_count",
    "outcome",
    "reason",
    "code",
    "latency_ms",
)


def log_context(**fields: Any) -> dict[str, Any]:
    """Sanitized correlation context: identifiers only, never payload secrets."""

    return {
        key: str(value)
        for key, value in fields.items()
        if key in ALLOWED_LOG_FIELDS and value is not None
    }


def log_event(message: str, **fields: Any) -> None:
    logger.info(message, extra={"fields": log_context(**fields)})


def log_failure(message: str, **fields: Any) -> None:
    logger.warning(message, extra={"fields": log_context(**fields)})


@dataclass(slots=True)
class LeaderboardMetrics:
    """Current Top-1 identity and update-latency samples for the demo dashboard."""

    update_latency_ms: list[float] = field(default_factory=list)
    top_one: dict[str, str] = field(default_factory=dict)
    changed_projections: int = 0
    unchanged_projections: int = 0
    published_events: int = 0
    publication_failures: int = 0

    # -- ProjectionObserver --------------------------------------------------

    def projection_changed(
        self,
        outcome: ProjectionOutcome,
        *,
        latency_ms: float,
        source: UpdateSource | None,
    ) -> None:
        self.changed_projections += 1
        self.update_latency_ms.append(latency_ms)
        del self.update_latency_ms[:-500]
        if outcome.top_one is not None:
            self.top_one[str(outcome.leaderboard_id)] = str(
                outcome.top_one.candidate.evaluation_result_id
            )
        log_event(
            "leaderboard_projection_changed",
            leaderboard_id=outcome.leaderboard_id,
            projection_version=outcome.projection_version,
            entry_count=outcome.entry_count,
            scope_key=outcome.scope_key,
            latency_ms=round(latency_ms, 3),
            evaluation_result_id=source.evaluation_result_id if source else None,
            request_id=source.request_id if source else None,
            outcome="CHANGED",
        )

    def projection_unchanged(
        self,
        outcome: ProjectionOutcome,
        *,
        source: UpdateSource | None,
    ) -> None:
        self.unchanged_projections += 1
        log_event(
            "leaderboard_projection_unchanged",
            leaderboard_id=outcome.leaderboard_id,
            projection_version=outcome.projection_version,
            evaluation_result_id=source.evaluation_result_id if source else None,
            request_id=source.request_id if source else None,
            outcome="UNCHANGED",
        )

    def events_published(self, count: int) -> None:
        self.published_events += count
        log_event("leaderboard_events_published", outcome=f"PUBLISHED:{count}")

    def publication_failed(self, event: LeaderboardUpdatedEvent) -> None:
        self.publication_failures += 1
        log_failure(
            "leaderboard_publication_failed",
            leaderboard_id=event.leaderboard_id,
            projection_version=event.projection_version,
            run_id=event.run_id,
            job_id=event.job_id,
            code="LEADERBOARD_PUBLICATION_FAILED",
        )

    # -- reporting -----------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        samples = sorted(self.update_latency_ms)
        index = max(0, int(len(samples) * 0.95) - 1)
        return {
            "updateSamples": len(samples),
            "updateLatencyP95Ms": samples[index] if samples else None,
            "changedProjections": self.changed_projections,
            "unchangedProjections": self.unchanged_projections,
            "publishedEvents": self.published_events,
            "publicationFailures": self.publication_failures,
            "topOne": dict(self.top_one),
        }
