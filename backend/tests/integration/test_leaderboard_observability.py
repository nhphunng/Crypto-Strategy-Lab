"""Correlation propagation and sanitized leaderboard observability."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest

from crypto_lab.application.leaderboard.ports import RecordingPublisher, UpdateSource
from crypto_lab.application.leaderboard.publish_leaderboard_updates import (
    PublishLeaderboardUpdates,
)
from crypto_lab.application.leaderboard.update_leaderboard import UpdateLeaderboard
from crypto_lab.domain.leaderboard.policy import (
    LeaderboardIdentity,
    LeaderboardScope,
    RankMetric,
    ScoringPolicyRef,
)
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.observability.leaderboard import (
    ALLOWED_LOG_FIELDS,
    LeaderboardMetrics,
    log_context,
)
from crypto_lab.infrastructure.persistence.repositories.leaderboard_repository import (
    SqlAlchemyLeaderboardRepository,
)
from tests.fixtures.leaderboard import LeaderboardFixture

pytestmark = pytest.mark.integration


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 13, 3, 30, tzinfo=UTC)


def identity(fixture: LeaderboardFixture) -> LeaderboardIdentity:
    return LeaderboardIdentity(
        scope=LeaderboardScope(pair=fixture.pair, timeframe=Timeframe(fixture.timeframe)),
        policy=ScoringPolicyRef(fixture.scoring_policy_id, fixture.scoring_policy_version),
        rank_metric=RankMetric.OVERALL_SCORE,
        k=10,
    )


def test_log_context_drops_unknown_and_sensitive_fields() -> None:
    context = log_context(
        request_id="req-1",
        run_id="run-1",
        password="secret",
        connection_string="postgresql://user:pass@host/db",
    )

    assert context == {"request_id": "req-1", "run_id": "run-1"}
    assert "password" not in ALLOWED_LOG_FIELDS


async def test_projection_change_records_latency_top_one_and_correlation(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    metrics = LeaderboardMetrics()
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    use_case = UpdateLeaderboard(repository, FixedClock(), metrics)

    with caplog.at_level(logging.INFO, logger="crypto_lab.leaderboard"):
        outcome = await use_case.for_identity(
            identity(seeded_leaderboard),
            source=UpdateSource(
                evaluation_result_id=seeded_leaderboard.top_one_evaluation_id,
                request_id="req-observability",
            ),
        )

    snapshot = metrics.snapshot()
    assert snapshot["changedProjections"] == 1
    assert snapshot["updateSamples"] == 1
    assert snapshot["updateLatencyP95Ms"] is not None
    assert snapshot["topOne"][str(outcome.leaderboard_id)] == str(
        seeded_leaderboard.top_one_evaluation_id
    )
    record = next(
        item for item in caplog.records if item.message == "leaderboard_projection_changed"
    )
    fields = record.fields  # type: ignore[attr-defined]
    assert fields["request_id"] == "req-observability"
    assert fields["projection_version"] == "1"
    assert fields["outcome"] == "CHANGED"


async def test_unchanged_projection_is_recorded_without_a_new_event(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    metrics = LeaderboardMetrics()
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    use_case = UpdateLeaderboard(repository, FixedClock(), metrics)
    await use_case.for_identity(identity(seeded_leaderboard))

    await use_case.for_evaluation(seeded_leaderboard.top_one_evaluation_id)

    snapshot = metrics.snapshot()
    assert snapshot["changedProjections"] == 1
    assert snapshot["unchangedProjections"] == 1


async def test_publication_counters_track_delivery(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    metrics = LeaderboardMetrics()
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    clock = FixedClock()
    await UpdateLeaderboard(repository, clock, metrics).for_identity(identity(seeded_leaderboard))
    dispatcher = PublishLeaderboardUpdates(
        repository,
        RecordingPublisher(),
        clock,
        observer=metrics,
    )

    await dispatcher.dispatch_once()

    assert metrics.snapshot()["publishedEvents"] == 1
    assert metrics.snapshot()["publicationFailures"] == 0


async def test_failed_publication_is_logged_without_internal_details(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class BrokenPublisher:
        async def publish(self, event: object) -> None:
            raise ConnectionError("postgresql://user:secret@host/db unreachable")

    metrics = LeaderboardMetrics()
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    clock = FixedClock()
    await UpdateLeaderboard(repository, clock, metrics).for_identity(identity(seeded_leaderboard))
    dispatcher = PublishLeaderboardUpdates(repository, BrokenPublisher(), clock, observer=metrics)

    with caplog.at_level(logging.WARNING, logger="crypto_lab.leaderboard"):
        published = await dispatcher.dispatch_once()

    assert published == 0
    assert metrics.snapshot()["publicationFailures"] == 1
    record = next(
        item for item in caplog.records if item.message == "leaderboard_publication_failed"
    )
    rendered = str(record.fields)  # type: ignore[attr-defined]
    assert "secret" not in rendered
    assert "postgresql" not in rendered
