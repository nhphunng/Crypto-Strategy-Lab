import pytest
from tests.fixtures.strategy.factories import context, definition

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.implementations.support_resistance import (
    SupportResistanceStrategy,
)
from crypto_lab.domain.strategy.signal import HistoryState, SignalAction, SignalPhase


def test_support_resistance_prior_levels_and_repeatability() -> None:
    strategy = SupportResistanceStrategy()
    selected = definition(strategy, {"lookback": 3, "tolerancePercent": "1"})
    supplied = context(["10", "12", "11", "10.05", "11.95", "11"])

    first = strategy.analyze(selected, supplied)

    assert first == strategy.analyze(selected, supplied)
    assert [signal.action for signal in first.signals] == [
        SignalAction.HOLD,
        SignalAction.HOLD,
        SignalAction.HOLD,
        SignalAction.BUY,
        SignalAction.SELL,
        SignalAction.HOLD,
    ]
    assert first.signals[2].phase is SignalPhase.WARMUP
    assert first.signals[3].phase is SignalPhase.EVALUATED
    assert first.history_state is HistoryState.EVALUABLE


def test_support_resistance_is_prefix_stable_without_future_lookahead() -> None:
    strategy = SupportResistanceStrategy()
    selected = definition(strategy, {"lookback": 2, "tolerancePercent": "1"})
    prefix = strategy.analyze(selected, context(["10", "12", "10.05"]))
    extended = strategy.analyze(selected, context(["10", "12", "10.05", "100"]))

    prefix_decisions = tuple(
        (signal.timestamp, signal.action, signal.phase, signal.reason) for signal in prefix.signals
    )
    extended_decisions = tuple(
        (signal.timestamp, signal.action, signal.phase, signal.reason)
        for signal in extended.signals
    )
    assert extended_decisions[: len(prefix.signals)] == prefix_decisions


def test_support_resistance_empty_insufficient_and_parameter_validation() -> None:
    strategy = SupportResistanceStrategy()
    selected = definition(strategy, {"lookback": 3})

    assert strategy.analyze(selected, context([])).history_state is HistoryState.EMPTY
    result = strategy.analyze(selected, context(["1", "2", "3"]))
    assert result.history_state is HistoryState.INSUFFICIENT

    with pytest.raises(StrategyError) as caught:
        strategy.validate_parameters({"lookback": 1})
    assert caught.value.category is ErrorCategory.INVALID_PARAMETERS
