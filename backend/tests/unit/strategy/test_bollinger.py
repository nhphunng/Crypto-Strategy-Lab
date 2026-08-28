import pytest
from tests.fixtures.strategy.factories import context, definition

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.implementations.bollinger import BollingerBandsStrategy
from crypto_lab.domain.strategy.signal import HistoryState, SignalAction, SignalPhase


def test_bollinger_mean_reversion_signals_and_repeatability() -> None:
    strategy = BollingerBandsStrategy()
    selected = definition(strategy, {"period": 3, "standardDeviations": "1"})
    supplied = context(["10", "10", "10", "8", "12"])

    first = strategy.analyze(selected, supplied)

    assert first == strategy.analyze(selected, supplied)
    assert [signal.action for signal in first.signals] == [
        SignalAction.HOLD,
        SignalAction.HOLD,
        SignalAction.HOLD,
        SignalAction.BUY,
        SignalAction.SELL,
    ]
    assert first.signals[1].phase is SignalPhase.WARMUP
    assert first.signals[2].phase is SignalPhase.EVALUATED
    assert first.history_state is HistoryState.EVALUABLE


def test_bollinger_empty_insufficient_and_parameter_validation() -> None:
    strategy = BollingerBandsStrategy()
    selected = definition(strategy, {"period": 3})

    assert strategy.analyze(selected, context([])).history_state is HistoryState.EMPTY
    result = strategy.analyze(selected, context(["1", "2"]))
    assert result.history_state is HistoryState.INSUFFICIENT
    assert all(signal.action is SignalAction.HOLD for signal in result.signals)

    with pytest.raises(StrategyError) as caught:
        strategy.validate_parameters({"standardDeviations": "0"})
    assert caught.value.category is ErrorCategory.INVALID_PARAMETERS
