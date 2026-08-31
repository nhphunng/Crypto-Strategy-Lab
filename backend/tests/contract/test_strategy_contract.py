import json

import pytest

from crypto_lab.domain.strategy.implementations.bollinger import BollingerBandsStrategy
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.implementations.rsi import RsiStrategy
from crypto_lab.domain.strategy.implementations.support_resistance import (
    SupportResistanceStrategy,
)
from crypto_lab.domain.strategy.protocol import Strategy
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult
from tests.fixtures.strategy.factories import context, definition


@pytest.mark.parametrize(
    ("strategy", "parameters"),
    (
        (MovingAverageStrategy(), {"period": 2}),
        (RsiStrategy(), {"period": 2}),
        (BollingerBandsStrategy(), {"period": 2, "standardDeviations": "1"}),
        (SupportResistanceStrategy(), {"lookback": 2, "tolerancePercent": "1"}),
    ),
)
def test_repeated_analysis_has_byte_equivalent_canonical_content(
    strategy: Strategy, parameters: dict[str, object]
) -> None:
    supplied = context(["1", "2", "1", "3"])
    result = strategy.analyze(definition(strategy, parameters), supplied)
    assert isinstance(result, StrategyAnalysisResult)
    canonical = json.dumps(
        [(item.id, item.timestamp.isoformat(), item.action, item.phase) for item in result.signals],
        separators=(",", ":"),
    )
    for _ in range(9):
        repeated = strategy.analyze(result.strategy_definition, supplied)
        assert isinstance(repeated, StrategyAnalysisResult)
        assert (
            json.dumps(
                [
                    (item.id, item.timestamp.isoformat(), item.action, item.phase)
                    for item in repeated.signals
                ],
                separators=(",", ":"),
            )
            == canonical
        )
