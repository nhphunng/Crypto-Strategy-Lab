from __future__ import annotations

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import profitable


def test_evaluation_consumes_only_immutable_backtest_result() -> None:
    configuration, candles, analysis, policy = profitable()
    backtest = execute_backtest(configuration, candles, analysis, policy, created_at=NOW)
    del analysis, policy
    metrics = calculate_metrics(backtest)
    assert metrics.number_of_trades == len(backtest.trades)
    assert metrics.total_return > 0
