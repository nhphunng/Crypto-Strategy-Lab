import json

from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from tests.fixtures.strategy.factories import context, definition


def test_repeated_analysis_has_byte_equivalent_canonical_content() -> None:
    strategy = MovingAverageStrategy()
    result = strategy.analyze(definition(strategy, {"period": 2}), context(["1", "2", "1", "3"]))
    canonical = json.dumps(
        [(item.id, item.timestamp.isoformat(), item.action, item.phase) for item in result.signals],
        separators=(",", ":"),
    )
    for _ in range(9):
        repeated = strategy.analyze(result.strategy_definition, context(["1", "2", "1", "3"]))
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
