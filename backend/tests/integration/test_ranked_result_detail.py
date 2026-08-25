"""PostgreSQL reads for ranked-result provenance, markers, and Trades."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from crypto_lab.application.leaderboard.errors import LeaderboardError
from crypto_lab.application.leaderboard.get_ranked_result import GetRankedResult
from crypto_lab.application.leaderboard.ports import AvailabilityState, MarkerType
from crypto_lab.application.leaderboard.update_leaderboard import UpdateLeaderboard
from crypto_lab.domain.leaderboard.policy import (
    LeaderboardIdentity,
    LeaderboardScope,
    RankMetric,
    ScoringPolicyRef,
)
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.repositories.leaderboard_repository import (
    SqlAlchemyLeaderboardRepository,
    SqlAlchemyRankedResultReader,
)
from tests.fixtures.leaderboard import LeaderboardFixture

pytestmark = pytest.mark.integration

START = datetime(2026, 7, 1, tzinfo=UTC)


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


async def prepare(database: Database, fixture: LeaderboardFixture):
    repository = SqlAlchemyLeaderboardRepository(database.sessions)
    await UpdateLeaderboard(repository, FixedClock()).for_identity(identity(fixture))
    snapshot = await repository.read_snapshot(identity(fixture))
    assert snapshot is not None
    return snapshot.leaderboard_id, GetRankedResult(SqlAlchemyRankedResultReader(database.sessions))


async def test_detail_joins_immutable_upstream_provenance(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    view = await ranked_results.detail(board, seeded_leaderboard.top_one_evaluation_id)

    assert view.entry.rank == 1
    assert view.provenance.strategy_version == "3"
    assert view.provenance.dataset_id == seeded_leaderboard.dataset_id
    assert len(view.provenance.result_checksum) == 64
    assert view.provenance.execution_config["feeRate"] == "0.0004"
    assert view.availability.overlays.state is AvailabilityState.UNAVAILABLE


async def test_visualization_aligns_markers_to_recorded_coordinates(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    view = await ranked_results.visualization(
        board,
        seeded_leaderboard.top_one_evaluation_id,
        START,
        START + timedelta(days=1),
    )

    candle_times = {candle.open_time for candle in view.candles}
    for marker in view.markers:
        assert marker.time in candle_times
        assert marker.price is not None
    assert view.unaligned_markers
    assert view.unaligned_markers[0].marker.price is None
    assert view.unaligned_markers[0].marker.time not in candle_times


async def test_entry_and_exit_markers_reconcile_with_recorded_trades(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    view = await ranked_results.visualization(
        board,
        seeded_leaderboard.top_one_evaluation_id,
        START,
        START + timedelta(days=1),
    )
    trades = await ranked_results.trades(board, seeded_leaderboard.top_one_evaluation_id)

    entries = {
        marker.trade_id: marker for marker in view.markers if marker.type is MarkerType.ENTRY
    }
    exits = {marker.trade_id: marker for marker in view.markers if marker.type is MarkerType.EXIT}
    for trade in trades.items:
        assert entries[trade.trade_id].time == trade.entry_time
        assert entries[trade.trade_id].price == trade.entry_price
        assert exits[trade.trade_id].time == trade.exit_time
        assert exits[trade.trade_id].price == trade.exit_price


async def test_partial_range_reports_partial_availability(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    view = await ranked_results.visualization(
        board,
        seeded_leaderboard.top_one_evaluation_id,
        START,
        START + timedelta(hours=2),
    )

    assert view.availability.candles.state is AvailabilityState.AVAILABLE
    assert view.availability.signals.state is AvailabilityState.PARTIAL
    assert view.availability.signals.reason


async def test_no_trade_result_keeps_candles_and_signals_inspectable(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    view = await ranked_results.visualization(
        board,
        seeded_leaderboard.no_trade_evaluation_id,
        START,
        START + timedelta(days=1),
    )
    trades = await ranked_results.trades(board, seeded_leaderboard.no_trade_evaluation_id)

    assert view.candles
    assert any(marker.type is MarkerType.HOLD for marker in view.markers)
    assert view.availability.trades.state is AvailabilityState.EMPTY
    assert trades.total == 0


async def test_oversized_range_is_rejected_before_reading_candles(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    with pytest.raises(LeaderboardError) as error:
        await ranked_results.visualization(
            board,
            seeded_leaderboard.top_one_evaluation_id,
            START,
            START + timedelta(days=365),
        )

    assert error.value.descriptor.code == "LEADERBOARD_RANGE_INVALID"


async def test_entry_outside_the_projection_is_not_readable(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)

    with pytest.raises(LeaderboardError) as error:
        await ranked_results.detail(board, seeded_leaderboard.ineligible_evaluation_id)

    assert error.value.descriptor.code == "LEADERBOARD_ENTRY_NOT_FOUND"
