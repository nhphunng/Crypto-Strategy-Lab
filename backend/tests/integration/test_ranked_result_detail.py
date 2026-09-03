"""PostgreSQL reads for ranked-result provenance, markers, and Trades."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from crypto_lab.api.schemas.leaderboards import visualization_to_dto
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
from crypto_lab.infrastructure.persistence.backtest_models import BacktestTradeRow
from crypto_lab.infrastructure.persistence.evaluation_models import EvaluationResultRow
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


@pytest.mark.parametrize("milliseconds_before_end", [1, 2])
async def test_exit_at_candle_close_keeps_execution_time_and_uses_exact_candle(
    leaderboard_database: Database,
    seeded_leaderboard: LeaderboardFixture,
    milliseconds_before_end: int,
) -> None:
    board, ranked_results = await prepare(leaderboard_database, seeded_leaderboard)
    exit_time = START + timedelta(days=1) - timedelta(milliseconds=milliseconds_before_end)
    async with leaderboard_database.sessions() as session, session.begin():
        evaluation = await session.get(
            EvaluationResultRow, seeded_leaderboard.top_one_evaluation_id
        )
        trade = await session.scalar(
            select(BacktestTradeRow)
            .where(BacktestTradeRow.backtest_result_id == evaluation.backtest_result_id)
            .order_by(BacktestTradeRow.sequence)
        )
        trade.exit_time = exit_time
        trade_id, exit_price = trade.id, trade.exit_price

    view = await ranked_results.visualization(
        board, seeded_leaderboard.top_one_evaluation_id, START, START + timedelta(days=1)
    )
    exits = [
        marker
        for marker in view.markers
        if marker.trade_id == trade_id and marker.type is MarkerType.EXIT
    ]
    if milliseconds_before_end == 1:
        assert len(exits) == 1
        assert exits[0].time == exit_time
        assert exits[0].price == exit_price
        assert exits[0].candle_time == START + timedelta(hours=23, minutes=45)
        dto = visualization_to_dto(view).model_dump(by_alias=True)
        marker = next(item for item in dto["markers"] if item["id"] == exits[0].id)
        assert marker["time"] == "2026-07-01T23:59:59.999Z"
        assert marker["candleTime"] == "2026-07-01T23:45:00.000Z"
        trades = await ranked_results.trades(board, seeded_leaderboard.top_one_evaluation_id)
        assert (
            next(item for item in trades.items if item.trade_id == trade_id).exit_time == exit_time
        )
    else:
        # An unmatched timestamp must not be snapped to a nearby Candle.
        assert not exits
        marker = next(
            item.marker
            for item in view.unaligned_markers
            if item.marker.trade_id == trade_id and item.marker.type is MarkerType.EXIT
        )
        assert marker.time == exit_time
        assert marker.candle_time is None


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
