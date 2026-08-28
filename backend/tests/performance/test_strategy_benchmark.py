from statistics import quantiles
from time import perf_counter

import pytest

from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from tests.fixtures.strategy.factories import context, definition


@pytest.mark.performance
def test_ten_thousand_candle_strategy_execution_is_bounded() -> None:
    strategy = MovingAverageStrategy()
    selected = definition(strategy, {"period": 20})
    supplied = context([str(100 + index % 17) for index in range(10_000)])
    samples = []
    fingerprints = set()
    for _ in range(20):
        started = perf_counter()
        result = strategy.analyze(selected, supplied)
        samples.append(perf_counter() - started)
        assert len(result.signals) == 10_000
        fingerprints.add(
            tuple((signal.id, signal.action, signal.phase) for signal in result.signals)
        )
    assert len(fingerprints) == 1
    assert quantiles(samples, n=100)[94] < 1


@pytest.mark.performance
def test_strategy_discovery_p95_is_below_three_hundred_milliseconds() -> None:
    registry = build_strategy_registry()
    samples = []
    for _ in range(100):
        started = perf_counter()
        assert len(registry.discover()) == 4
        samples.append(perf_counter() - started)
    assert quantiles(samples, n=100)[94] < 0.3


@pytest.mark.performance
async def test_generation_request_acknowledgement_is_below_two_seconds() -> None:
    from datetime import UTC, datetime

    from crypto_lab.application.strategies.generate_strategies import (
        GenerateStrategies,
        GenerateStrategiesCommand,
    )
    from crypto_lab.domain.strategy.generation import GenerationSourceType

    class Repository:
        async def save_request(self, request):
            self.request = request

    class Clock:
        def now(self):
            return datetime(2026, 1, 1, tzinfo=UTC)

    use_case = GenerateStrategies(None, None, None, None, Repository(), Clock())  # type: ignore[arg-type]
    started = perf_counter()
    request = await use_case.submit(
        GenerateStrategiesCommand(GenerationSourceType.NATURAL_LANGUAGE, "rules")
    )
    assert request.status.value == "RECEIVED"
    assert perf_counter() - started < 2
