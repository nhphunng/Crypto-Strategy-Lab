"""REQUIREMENT.md section 21: every completed evaluation enters the Leaderboard.

These tests cover the seam between the Evaluation feature and the leaderboard
projection: an evaluation that completes must rank without anyone calling the
leaderboard by hand.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from crypto_lab.application.leaderboard.ports import RecordingPublisher
from crypto_lab.application.leaderboard.publish_leaderboard_updates import (
    LeaderboardIngestion,
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
from crypto_lab.infrastructure.persistence.leaderboard_models import LeaderboardEntryRow
from crypto_lab.infrastructure.persistence.repositories.leaderboard_repository import (
    SqlAlchemyLeaderboardRepository,
)
from tests.fixtures.leaderboard import LeaderboardFixture, add_qualifying_candidate

pytestmark = pytest.mark.integration


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 28, 6, 0, tzinfo=UTC)


def identity(fixture: LeaderboardFixture) -> LeaderboardIdentity:
    return LeaderboardIdentity(
        scope=LeaderboardScope(pair=fixture.pair, timeframe=Timeframe(fixture.timeframe)),
        policy=ScoringPolicyRef(fixture.scoring_policy_id, fixture.scoring_policy_version),
        rank_metric=RankMetric.OVERALL_SCORE,
        k=10,
    )


def build(database: Database) -> tuple[LeaderboardIngestion, RecordingPublisher, object]:
    repository = SqlAlchemyLeaderboardRepository(database.sessions)
    clock = FixedClock()
    publisher = RecordingPublisher()
    dispatcher = PublishLeaderboardUpdates(repository, publisher, clock)
    updater = UpdateLeaderboard(repository, clock)
    return LeaderboardIngestion(updater, dispatcher), publisher, repository


async def test_a_completed_evaluation_enters_the_leaderboard_without_a_manual_step(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    ingestion, publisher, repository = build(leaderboard_database)
    await UpdateLeaderboard(repository, FixedClock()).for_identity(identity(seeded_leaderboard))
    async with leaderboard_database.sessions() as session, session.begin():
        newcomer = await add_qualifying_candidate(session)

    await ingestion.on_evaluation_completed(newcomer, request_id="req-auto")

    snapshot = await repository.read_snapshot(identity(seeded_leaderboard))
    assert snapshot is not None
    assert snapshot.entries[0].candidate.evaluation_result_id == newcomer
    entering = [event for event in publisher.events if newcomer in event.added]
    assert len(entering) == 1


async def test_a_lower_scoring_evaluation_does_not_displace_the_top_of_the_board(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    """Section 22: a candidate enters Top-K only when it out-scores the last row."""

    ingestion, _, repository = build(leaderboard_database)
    await UpdateLeaderboard(repository, FixedClock()).for_identity(identity(seeded_leaderboard))
    before = await repository.read_snapshot(identity(seeded_leaderboard))
    assert before is not None

    async with leaderboard_database.sessions() as session, session.begin():
        # Section 22: below the tenth score, so it must stay off the board.
        weak = await add_qualifying_candidate(session, index=31, score=Decimal("12"))

    await ingestion.on_evaluation_completed(weak, request_id="req-auto")

    after = await repository.read_snapshot(identity(seeded_leaderboard))
    assert after is not None
    assert after.entries[0].candidate.evaluation_result_id == (
        before.entries[0].candidate.evaluation_result_id
    )
    assert len(after.entries) == 10
    assert all(entry.candidate.evaluation_result_id != weak for entry in after.entries)


async def test_repeated_ingestion_of_one_evaluation_ranks_it_once(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    ingestion, publisher, repository = build(leaderboard_database)
    await UpdateLeaderboard(repository, FixedClock()).for_identity(identity(seeded_leaderboard))
    async with leaderboard_database.sessions() as session, session.begin():
        newcomer = await add_qualifying_candidate(session)

    await ingestion.on_evaluation_completed(newcomer)
    await ingestion.on_evaluation_completed(newcomer)
    await ingestion.on_evaluation_completed(newcomer)

    async with leaderboard_database.sessions() as session:
        rows = await session.scalar(
            select(func.count())
            .select_from(LeaderboardEntryRow)
            .where(LeaderboardEntryRow.evaluation_result_id == newcomer)
        )
    assert rows == 1
    assert len([event for event in publisher.events if newcomer in event.added]) == 1
