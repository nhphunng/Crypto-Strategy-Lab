from __future__ import annotations

from decimal import Decimal

from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import losing, no_loss, no_trade, profitable

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.evaluation.metrics import calculate_metrics


def _metrics(scenario):
    config, candles, analysis, policy = scenario()
    return calculate_metrics(execute_backtest(config, candles, analysis, policy, created_at=NOW))


def test_required_metrics_for_profit_and_loss() -> None:
    profit = _metrics(profitable)
    loss = _metrics(losing)
    assert profit.total_return == Decimal("20.000000000000000000")
    assert profit.win_rate == Decimal("100.000000000000000000")
    assert profit.number_of_trades == 1
    assert loss.total_return == Decimal("-20.000000000000000000")
    assert loss.max_drawdown > 0


def test_no_trade_and_undefined_metric_semantics() -> None:
    metrics = _metrics(no_trade)
    assert metrics.total_return == metrics.win_rate == metrics.max_drawdown == 0
    assert metrics.number_of_trades == 0
    assert metrics.profit_factor is None
    assert metrics.sharpe_ratio is None
    assert _metrics(no_loss).profit_factor is None
