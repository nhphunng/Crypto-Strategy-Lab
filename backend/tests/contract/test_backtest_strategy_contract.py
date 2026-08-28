from __future__ import annotations

from dataclasses import replace

import pytest

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode, NoOpCode
from crypto_lab.domain.strategy.signal import SignalPhase
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import no_trade


def test_exact_ordered_generic_signals_are_consumed() -> None:
    configuration, candles, analysis, policy = no_trade()
    first = replace(analysis.signals[0], phase=SignalPhase.WARMUP)
    analysis = replace(analysis, signals=(first, *analysis.signals[1:]))
    result = execute_backtest(configuration, candles, analysis, policy, created_at=NOW)
    assert result.signals[0].no_op_code is NoOpCode.WARMUP


def test_misaligned_signal_is_rejected_without_repair() -> None:
    configuration, candles, analysis, policy = no_trade()
    bad = replace(analysis.signals[1], timestamp=analysis.signals[0].timestamp)
    analysis = replace(analysis, signals=(analysis.signals[0], bad, analysis.signals[2]))
    with pytest.raises(BacktestError) as caught:
        execute_backtest(configuration, candles, analysis, policy, created_at=NOW)
    assert caught.value.code is BacktestErrorCode.SIGNAL_MISALIGNED
