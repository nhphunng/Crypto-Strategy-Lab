from __future__ import annotations

from time import perf_counter

import pytest

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.strategy.signal import SignalAction
from tests.fixtures.backtest_evaluation.cross_feature import NOW, deterministic_inputs
from tests.fixtures.backtest_evaluation.persistence import BacktestPersistenceContext


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


@pytest.mark.performance
@pytest.mark.integration
async def test_bounded_postgresql_reads_meet_interactive_p95(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    repository = persisted_backtest.repository
    result_id = persisted_backtest.result.id
    durations: list[float] = []
    for _ in range(100):
        started = perf_counter()
        counts = await repository.result_counts(result_id)
        trades, _ = await repository.list_trades(result_id, None, 2)
        equity, _ = await repository.list_equity(result_id, None, 2)
        durations.append(perf_counter() - started)
        assert counts == (2, 5)
        assert len(trades) == len(equity) == 2

    p95 = sorted(durations)[94]
    print(f"Feature004 bounded PostgreSQL read p95={p95 * 1000:.3f}ms")
    assert p95 < 0.300
