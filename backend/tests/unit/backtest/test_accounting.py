from __future__ import annotations

from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import forced_close, redundant_signals

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.errors import NoOpCode
from crypto_lab.domain.backtest.trade import CloseReason


def test_redundant_signals_costs_and_equity_reconcile() -> None:
    config, candles, analysis, policy = redundant_signals()
    result = execute_backtest(config, candles, analysis, policy, created_at=NOW)
    assert result.signals[1].no_op_code is NoOpCode.ALREADY_LONG
    assert len(result.trades) == 1
    assert result.final_equity == result.equity_curve.points[-1].total_equity
    assert all(
        point.total_equity == point.cash + point.position_value
        for point in result.equity_curve.points
    )


def test_open_position_is_force_closed() -> None:
    config, candles, analysis, policy = forced_close()
    result = execute_backtest(config, candles, analysis, policy, created_at=NOW)
    assert result.trades[0].close_reason is CloseReason.END_OF_RANGE
    assert result.trades[0].exit_signal_snapshot_id is None
    assert result.equity_curve.points[-1].quantity == 0
