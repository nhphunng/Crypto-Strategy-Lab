from __future__ import annotations

from crypto_lab.domain.strategy.signal import SignalAction
from tests.fixtures.backtest_evaluation.cross_feature import deterministic_inputs


def profitable():
    return deterministic_inputs(
        (SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL, SignalAction.HOLD),
        ("100", "100", "120", "120"),
    )


def losing():
    return deterministic_inputs(
        (SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL, SignalAction.HOLD),
        ("100", "100", "80", "80"),
    )


def no_trade():
    return deterministic_inputs(
        (SignalAction.HOLD, SignalAction.HOLD, SignalAction.HOLD), ("100", "100", "100")
    )


def no_loss():
    return deterministic_inputs(
        (SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD), ("100", "100", "110")
    )


def zero_variance():
    return no_trade()


def redundant_signals():
    return deterministic_inputs(
        (SignalAction.BUY, SignalAction.BUY, SignalAction.SELL, SignalAction.SELL),
        ("100", "100", "110", "110"),
    )


def forced_close():
    return deterministic_inputs(
        (SignalAction.BUY, SignalAction.HOLD, SignalAction.HOLD), ("100", "100", "110")
    )
