from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.signal import SignalAction
from tests.fixtures.strategy.factories import context, definition


def test_result_contains_generic_exact_provenance_and_ordered_signals() -> None:
    strategy = MovingAverageStrategy()
    selected = definition(strategy, {"period": 2})
    supplied = context(["1", "2", "1", "3"])
    result = strategy.analyze(selected, supplied)
    assert result.strategy_definition.id == selected.id
    assert result.context_provenance.dataset_id == supplied.dataset_id
    assert tuple(item.sequence for item in result.signals) == tuple(range(4))
    assert set(item.action for item in result.signals) <= set(SignalAction)
