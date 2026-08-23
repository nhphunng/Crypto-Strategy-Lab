from tests.fixtures.strategy.factories import context, definition

from crypto_lab.domain.strategy.implementations.rsi import RsiStrategy
from crypto_lab.domain.strategy.signal import HistoryState, SignalAction, SignalPhase


def test_rsi_wilder_threshold_exit_and_repeatability() -> None:
    strategy = RsiStrategy()
    selected = definition(strategy, {"period": 2, "lowerThreshold": "30", "upperThreshold": "70"})
    supplied = context(["10", "9", "8", "10", "12", "10"])
    first = strategy.analyze(selected, supplied)
    assert first == strategy.analyze(selected, supplied)
    assert first.signals[0].phase is SignalPhase.WARMUP
    assert first.signals[3].action is SignalAction.BUY
    assert first.history_state is HistoryState.EVALUABLE


def test_rsi_constant_prices_are_neutral_once_evaluable() -> None:
    strategy = RsiStrategy()
    selected = definition(strategy, {"period": 2})
    result = strategy.analyze(selected, context(["1", "1", "1", "1"]))
    assert result.signals[-1].phase is SignalPhase.EVALUATED
    assert result.signals[-1].action is SignalAction.HOLD
