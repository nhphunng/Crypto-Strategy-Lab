"""Structured leaderboard log context and lightweight in-process metrics."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("crypto_lab.leaderboard")


@dataclass(slots=True)
class LeaderboardMetrics:
    """Current Top-1 identity and update-latency samples for the demo dashboard."""

    update_latency_ms: list[float] = field(default_factory=list)
    top_one: dict[str, str] = field(default_factory=dict)
    published_events: int = 0
    duplicate_suppressed: int = 0

    def record_update(self, leaderboard_id: str, latency_ms: float) -> None:
        self.update_latency_ms.append(latency_ms)
        del self.update_latency_ms[:-500]
        logger.info(
            "leaderboard_projection_updated",
            extra={"fields": {"leaderboard_id": leaderboard_id, "latency_ms": latency_ms}},
        )

    def record_top_one(self, leaderboard_id: str, summary: dict[str, str] | None) -> None:
        if summary is None:
            self.top_one.pop(leaderboard_id, None)
            return
        self.top_one[leaderboard_id] = summary.get("evaluationResultId", "")

    def record_published(self, count: int = 1) -> None:
        self.published_events += count

    def record_duplicate_suppressed(self) -> None:
        self.duplicate_suppressed += 1

    def snapshot(self) -> dict[str, Any]:
        samples = sorted(self.update_latency_ms)
        p95 = samples[int(len(samples) * 0.95) - 1] if samples else None
        return {
            "updateSamples": len(samples),
            "updateLatencyP95Ms": p95,
            "publishedEvents": self.published_events,
            "duplicateSuppressed": self.duplicate_suppressed,
            "topOne": dict(self.top_one),
        }


def log_context(**fields: Any) -> dict[str, Any]:
    """Sanitized correlation context: identifiers only, never payload secrets."""

    allowed = (
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
        "outcome",
        "reason",
        "code",
    )
    return {
        key: str(value) for key, value in fields.items() if key in allowed and value is not None
    }


def log_event(message: str, **fields: Any) -> None:
    logger.info(message, extra={"fields": log_context(**fields)})


def log_failure(message: str, **fields: Any) -> None:
    logger.warning(message, extra={"fields": log_context(**fields)})
