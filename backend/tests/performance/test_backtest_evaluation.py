from __future__ import annotations

from time import perf_counter

import pytest

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.strategy.signal import SignalAction
from tests.fixtures.backtest_evaluation.cross_feature import NOW, deterministic_inputs


@pytest.mark.performance
def test_ten_thousand_candle_backtest_completes_within_five_seconds() -> None:
    count = 10_000
    actions = tuple(SignalAction.HOLD for _ in range(count))
    prices = tuple(str(100 + index % 20) for index in range(count))
    configuration, candles, analysis, policy = deterministic_inputs(actions, prices)
    started = perf_counter()
    result = execute_backtest(configuration, candles, analysis, policy, created_at=NOW)
    metrics = calculate_metrics(result)
    duration = perf_counter() - started
    assert len(result.equity_curve.points) == count
    assert metrics.number_of_trades == 0
    assert duration < 5
