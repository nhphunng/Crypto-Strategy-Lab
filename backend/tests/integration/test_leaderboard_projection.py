"""PostgreSQL projection behaviour: identity, atomicity, and idempotency."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from crypto_lab.application.leaderboard.ports import (
    LeaderboardUpdatedEvent,
    RecordingPublisher,
    RunState,
    UpdateSource,
)
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
from crypto_lab.infrastructure.persistence.leaderboard_models import (
    LeaderboardEntryRow,
    LeaderboardRow,
    LeaderboardUpdateRecordRow,
)
from crypto_lab.infrastructure.persistence.repositories.leaderboard_repository import (
    SqlAlchemyLeaderboardRepository,
)
from tests.fixtures.leaderboard import LeaderboardFixture, add_qualifying_candidate

pytestmark = pytest.mark.integration


class FailingPublisher:
    """Publisher whose transport is unavailable for this attempt."""

    async def publish(self, event: LeaderboardUpdatedEvent) -> None:
        raise ConnectionError("event transport unavailable")


class FixedClock:
    def __init__(self) -> None:
        self._now = datetime(2026, 8, 13, 3, 30, tzinfo=UTC)

    def now(self) -> datetime:
        self._now = self._now.replace(microsecond=0)
        return self._now


def identity(fixture: LeaderboardFixture, *, k: int = 10, metric=RankMetric.OVERALL_SCORE):
    return LeaderboardIdentity(
        scope=LeaderboardScope(pair=fixture.pair, timeframe=Timeframe(fixture.timeframe)),
        policy=ScoringPolicyRef(fixture.scoring_policy_id, fixture.scoring_policy_version),
        rank_metric=metric,
        k=k,
    )


def updater(database: Database) -> UpdateLeaderboard:
    return UpdateLeaderboard(SqlAlchemyLeaderboardRepository(database.sessions), FixedClock())


async def test_projection_materializes_deterministic_top_k(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    use_case = UpdateLeaderboard(repository, FixedClock())

    outcome = await use_case.for_identity(identity(seeded_leaderboard))
    snapshot = await repository.read_snapshot(identity(seeded_leaderboard))

    assert outcome.changed is True
    assert outcome.projection_version == 1
    assert snapshot is not None
    assert len(snapshot.entries) == 10
    assert [entry.rank for entry in snapshot.entries] == list(range(1, 11))
    assert tuple(
        entry.candidate.evaluation_result_id for entry in snapshot.entries
    ) == seeded_leaderboard.expected_top_ten


async def test_ineligible_candidate_never_enters_the_projection(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    outcome = await UpdateLeaderboard(repository, FixedClock()).for_identity(
        identity(seeded_leaderboard)
    )
    snapshot = await repository.read_snapshot(identity(seeded_leaderboard))

    assert snapshot is not None
    ranked = {entry.candidate.evaluation_result_id for entry in snapshot.entries}
    assert seeded_leaderboard.ineligible_evaluation_id not in ranked
    excluded = {item.evaluation_result_id for item in outcome.excluded}
    assert seeded_leaderboard.ineligible_evaluation_id in excluded


async def test_recomputing_the_same_inputs_is_an_idempotent_no_op(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    use_case = updater(leaderboard_database)
    source = UpdateSource(evaluation_result_id=seeded_leaderboard.top_one_evaluation_id)

    first = await use_case.for_identity(identity(seeded_leaderboard), source=source)
    second = await use_case.for_identity(identity(seeded_leaderboard), source=source)
    third = await use_case.for_identity(identity(seeded_leaderboard), source=source)

    assert first.changed is True
    assert second.changed is False
    assert third.changed is False
    assert second.projection_version == first.projection_version

    async with leaderboard_database.sessions() as session:
        entries = await session.scalar(select(func.count()).select_from(LeaderboardEntryRow))
        records = await session.scalar(
            select(func.count()).select_from(LeaderboardUpdateRecordRow)
        )
    assert entries == 10
    assert records == 1


async def test_duplicate_evaluation_delivery_creates_one_entry(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    use_case = updater(leaderboard_database)
    await use_case.for_identity(identity(seeded_leaderboard))

    await use_case.for_evaluation(seeded_leaderboard.top_one_evaluation_id)
    await use_case.for_evaluation(seeded_leaderboard.top_one_evaluation_id)

    async with leaderboard_database.sessions() as session:
        rows = (
            await session.scalars(
                select(LeaderboardEntryRow).where(
                    LeaderboardEntryRow.evaluation_result_id
                    == seeded_leaderboard.top_one_evaluation_id
                )
            )
        ).all()
    assert len(rows) == 1


async def test_a_different_k_or_metric_is_a_separate_projection(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    use_case = updater(leaderboard_database)

    await use_case.for_identity(identity(seeded_leaderboard, k=10))
    await use_case.for_identity(identity(seeded_leaderboard, k=3))
    await use_case.for_identity(
        identity(seeded_leaderboard, metric=RankMetric.MAX_DRAWDOWN),
    )

    async with leaderboard_database.sessions() as session:
        boards = (await session.scalars(select(LeaderboardRow))).all()
    assert len(boards) == 3
    assert sorted(board.entry_count for board in boards) == [3, 10, 10]


async def test_evaluation_completion_updates_every_matching_scope(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    use_case = updater(leaderboard_database)
    scoped = identity(seeded_leaderboard)
    unscoped = LeaderboardIdentity(
        scope=LeaderboardScope(),
        policy=scoped.policy,
        rank_metric=RankMetric.OVERALL_SCORE,
        k=10,
    )
    await use_case.for_identity(scoped)
    await use_case.for_identity(unscoped)

    outcomes = await use_case.for_evaluation(seeded_leaderboard.top_one_evaluation_id)

    assert len(outcomes) == 2
    assert all(outcome.changed is False for outcome in outcomes)


async def test_concurrent_updates_serialize_without_rank_conflicts(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    use_case = updater(leaderboard_database)
    target = identity(seeded_leaderboard)

    await asyncio.gather(
        use_case.for_identity(target),
        use_case.for_identity(target),
        use_case.for_identity(target),
    )

    async with leaderboard_database.sessions() as session:
        ranks = (
            await session.scalars(
                select(LeaderboardEntryRow.rank).order_by(LeaderboardEntryRow.rank)
            )
        ).all()
        board = await session.scalar(select(LeaderboardRow))
    assert list(ranks) == list(range(1, 11))
    assert board is not None
    assert board.projection_version == 1
    assert board.entry_count == 10


async def test_update_record_is_committed_with_the_projection_change(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    use_case = updater(leaderboard_database)
    outcome = await use_case.for_identity(
        identity(seeded_leaderboard),
        source=UpdateSource(evaluation_result_id=seeded_leaderboard.top_one_evaluation_id),
    )

    async with leaderboard_database.sessions() as session:
        record = await session.scalar(select(LeaderboardUpdateRecordRow))
    assert record is not None
    assert record.id == outcome.update_record_id
    assert record.projection_version == outcome.projection_version
    assert record.published_at is None
    assert record.event_type == "LEADERBOARD_UPDATED"
    assert len(record.added_ids) == 10


async def test_snapshot_exposes_immutable_provenance_for_every_row(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    await UpdateLeaderboard(repository, FixedClock()).for_identity(identity(seeded_leaderboard))

    snapshot = await repository.read_snapshot(identity(seeded_leaderboard))

    assert snapshot is not None
    for entry in snapshot.entries:
        candidate = entry.candidate
        assert candidate.strategy.strategy_version == "3"
        assert candidate.strategy.members
        assert candidate.dataset_id == seeded_leaderboard.dataset_id
        assert candidate.pair == seeded_leaderboard.pair
        assert candidate.policy.version == seeded_leaderboard.scoring_policy_version


async def test_dispatcher_publishes_committed_records_once(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    clock = FixedClock()
    publisher = RecordingPublisher()
    dispatcher = PublishLeaderboardUpdates(repository, publisher, clock)
    await UpdateLeaderboard(repository, clock).for_identity(
        identity(seeded_leaderboard),
        source=UpdateSource(evaluation_result_id=seeded_leaderboard.top_one_evaluation_id),
    )

    first = await dispatcher.dispatch_once()
    second = await dispatcher.dispatch_once()

    assert first == 1
    assert second == 0
    assert len(publisher.events) == 1
    event = publisher.events[0]
    assert event.projection_version == 1
    assert event.entry_count == 10
    assert event.top_one is not None
    assert event.top_one["evaluationResultId"] == str(seeded_leaderboard.top_one_evaluation_id)
    assert event.run_state is RunState.COMPLETED

    async with leaderboard_database.sessions() as session:
        record = await session.scalar(select(LeaderboardUpdateRecordRow))
    assert record is not None
    assert record.published_at is not None


async def test_publication_failure_is_retried_without_repeating_the_change(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    clock = FixedClock()
    await UpdateLeaderboard(repository, clock).for_identity(identity(seeded_leaderboard))

    failing = FailingPublisher()
    await PublishLeaderboardUpdates(repository, failing, clock).dispatch_once()
    async with leaderboard_database.sessions() as session:
        unpublished = await session.scalar(select(LeaderboardUpdateRecordRow))
    assert unpublished is not None
    assert unpublished.published_at is None

    recovered = RecordingPublisher()
    published = await PublishLeaderboardUpdates(repository, recovered, clock).dispatch_once()

    assert published == 1
    assert len(recovered.events) == 1
    async with leaderboard_database.sessions() as session:
        boards = (await session.scalars(select(LeaderboardRow))).all()
    assert [board.projection_version for board in boards] == [1]


async def test_evaluation_ingestion_publishes_only_visible_changes(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    clock = FixedClock()
    publisher = RecordingPublisher()
    dispatcher = PublishLeaderboardUpdates(repository, publisher, clock)
    use_case = UpdateLeaderboard(repository, clock)
    ingestion = LeaderboardIngestion(use_case, dispatcher)
    await use_case.for_identity(identity(seeded_leaderboard))
    await dispatcher.dispatch_once()
    published_after_materialization = len(publisher.events)

    await ingestion.on_evaluation_completed(seeded_leaderboard.top_one_evaluation_id)
    await ingestion.on_evaluation_completed(seeded_leaderboard.top_one_evaluation_id)

    assert len(publisher.events) == published_after_materialization


async def test_a_newly_completed_qualifying_evaluation_publishes_one_event(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    repository = SqlAlchemyLeaderboardRepository(leaderboard_database.sessions)
    clock = FixedClock()
    publisher = RecordingPublisher()
    dispatcher = PublishLeaderboardUpdates(repository, publisher, clock)
    use_case = UpdateLeaderboard(repository, clock)
    ingestion = LeaderboardIngestion(use_case, dispatcher)
    await use_case.for_identity(identity(seeded_leaderboard))
    await dispatcher.dispatch_once()
    baseline = len(publisher.events)

    async with leaderboard_database.sessions() as session, session.begin():
        newcomer = await add_qualifying_candidate(session)

    await ingestion.on_evaluation_completed(newcomer)
    await ingestion.on_evaluation_completed(newcomer)

    assert len(publisher.events) == baseline + 1
    event = publisher.events[-1]
    assert str(newcomer) in {str(item) for item in event.added}
    assert event.projection_version == 2

    snapshot = await repository.read_snapshot(identity(seeded_leaderboard))
    assert snapshot is not None
    assert len(snapshot.entries) == 10
    assert snapshot.entries[0].candidate.evaluation_result_id == newcomer
