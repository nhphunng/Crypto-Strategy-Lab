from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from tests.fixtures.backtest_evaluation.persistence import BacktestPersistenceContext

pytestmark = pytest.mark.integration


async def test_child_counts_and_order_round_trip_exactly(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    context = persisted_backtest
    loaded = await context.repository.get_result(context.result.id)
    counts = await context.repository.result_counts(context.result.id)

    assert loaded is not None
    assert counts == (2, 5)
    assert [item.sequence for item in loaded.trades] == [0, 1]
    assert [item.position for item in loaded.equity_curve.points] == list(range(5))
    assert loaded.final_equity == loaded.equity_curve.points[-1].total_equity


async def test_trade_and_equity_pagination_is_bounded_without_overlap(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    repository, result_id = persisted_backtest.repository, persisted_backtest.result.id
    first_trades, trade_cursor = await repository.list_trades(result_id, None, 1)
    second_trades, final_trade_cursor = await repository.list_trades(
        result_id, trade_cursor, 1
    )
    first_equity, equity_cursor = await repository.list_equity(result_id, None, 2)
    second_equity, next_equity_cursor = await repository.list_equity(
        result_id, equity_cursor, 2
    )
    final_equity, final_equity_cursor = await repository.list_equity(
        result_id, next_equity_cursor, 2
    )

    assert [item.sequence for item in first_trades + second_trades] == [0, 1]
    assert trade_cursor == "1"
    assert final_trade_cursor is None
    assert [item.position for item in first_equity + second_equity + final_equity] == [
        0,
        1,
        2,
        3,
        4,
    ]
    assert equity_cursor == "2"
    assert next_equity_cursor == "4"
    assert final_equity_cursor is None


async def test_retrieved_result_and_children_are_immutable_domain_values(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    first = await persisted_backtest.repository.get_result(persisted_backtest.result.id)
    second = await persisted_backtest.repository.get_result(persisted_backtest.result.id)

    assert first is not None and second is not None
    assert first == second
    assert first.result_checksum == persisted_backtest.result.result_checksum
    with pytest.raises(FrozenInstanceError):
        first.result_checksum = "0" * 64  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.trades[0].profit_loss = first.trades[0].profit_loss  # type: ignore[misc]
