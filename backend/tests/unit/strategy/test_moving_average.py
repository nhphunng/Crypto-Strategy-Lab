from tests.fixtures.strategy.factories import context, definition

from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.signal import HistoryState, SignalAction, SignalPhase


def test_ma_warmup_strict_crossing_equality_and_repeatability() -> None:
    strategy = MovingAverageStrategy()
    selected = definition(strategy, {"period": 2})
    supplied = context(["2", "1", "3", "2", "1", "1"])
    first = strategy.analyze(selected, supplied)
    second = strategy.analyze(selected, supplied)
    assert first == second
    assert [signal.action for signal in first.signals] == [
        SignalAction.HOLD,
        SignalAction.HOLD,
        SignalAction.BUY,
        SignalAction.SELL,
        SignalAction.HOLD,
        SignalAction.HOLD,
    ]
    assert first.signals[0].phase is SignalPhase.WARMUP
    assert first.signals[2].phase is SignalPhase.EVALUATED
    assert first.history_state is HistoryState.EVALUABLE


def test_ma_empty_and_insufficient_history() -> None:
    strategy = MovingAverageStrategy()
    selected = definition(strategy, {"period": 3})
    assert strategy.analyze(selected, context([])).history_state is HistoryState.EMPTY
    result = strategy.analyze(selected, context(["1", "2", "3"]))
    assert result.history_state is HistoryState.INSUFFICIENT
    assert all(signal.action is SignalAction.HOLD for signal in result.signals)
