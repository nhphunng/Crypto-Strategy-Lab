from __future__ import annotations

from dataclasses import replace

import pytest

from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import no_trade


def test_complete_dataset_is_consumed_without_provider_access() -> None:
    configuration, candles, analysis, policy = no_trade()
    result = execute_backtest(configuration, candles, analysis, policy, created_at=NOW)
    assert len(result.equity_curve.points) == len(candles)


@pytest.mark.parametrize("checksum", ["0" * 64, "f" * 64])
def test_dataset_checksum_mismatch_fails_closed(checksum: str) -> None:
    configuration, candles, analysis, policy = no_trade()
    with pytest.raises(BacktestError) as caught:
        execute_backtest(
            replace(configuration, dataset_checksum=checksum),
            candles,
            analysis,
            policy,
            created_at=NOW,
        )
    assert caught.value.code is BacktestErrorCode.DATASET_INTEGRITY_FAILED
