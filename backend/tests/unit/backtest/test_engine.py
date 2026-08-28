from __future__ import annotations

from dataclasses import replace

import pytest
from tests.fixtures.backtest_evaluation.cross_feature import NOW, deterministic_inputs

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode, NoOpCode
from crypto_lab.domain.backtest.trade import CloseReason
from crypto_lab.domain.strategy.signal import SignalAction


def test_next_open_execution_and_determinism() -> None:
    config, candles, analysis, policy = deterministic_inputs(
        (SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL, SignalAction.HOLD),
        ("90", "100", "110", "120"),
    )
    results = tuple(
        execute_backtest(config, candles, analysis, policy, created_at=NOW) for _ in range(100)
    )
    assert {result.result_checksum for result in results} == {results[0].result_checksum}
    trade = results[0].trades[0]
    assert trade.entry_reference_price == 100
    assert trade.exit_reference_price == 120
    assert trade.close_reason is CloseReason.SELL_SIGNAL


def test_final_candle_signal_never_opens_position() -> None:
    config, candles, analysis, policy = deterministic_inputs(
        (SignalAction.HOLD, SignalAction.HOLD, SignalAction.BUY), ("100", "100", "100")
    )
    result = execute_backtest(config, candles, analysis, policy, created_at=NOW)
    assert result.trades == ()
    assert result.signals[-1].no_op_code is NoOpCode.FINAL_CANDLE_SIGNAL


def test_checksum_corruption_fails_closed() -> None:
    config, candles, analysis, policy = deterministic_inputs((SignalAction.HOLD,) * 3, ("100",) * 3)
    with pytest.raises(BacktestError) as caught:
        execute_backtest(
            replace(config, dataset_checksum="0" * 64), candles, analysis, policy, created_at=NOW
        )
    assert caught.value.code is BacktestErrorCode.DATASET_INTEGRITY_FAILED
