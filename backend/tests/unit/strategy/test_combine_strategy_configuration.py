from decimal import Decimal
from importlib import import_module

from crypto_lab.domain.strategy.configuration import CombinationMethod
from crypto_lab.domain.strategy.signal import SignalAction


def test_weighted_actions_use_exact_decimal_thresholds() -> None:
    module = import_module("crypto_lab.application.strategies.combine_configuration")

    assert (
        module.combine_actions(
            CombinationMethod.WEIGHTED,
            (SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD),
            (Decimal("0.6"), Decimal("0.2"), Decimal("0.2")),
            SignalAction.HOLD,
            Decimal("0.3"),
            Decimal("-0.3"),
        )
        == (SignalAction.BUY, Decimal("0.4"))
    )


def test_majority_tie_uses_configured_action() -> None:
    module = import_module("crypto_lab.application.strategies.combine_configuration")

    assert module.combine_actions(
        CombinationMethod.MAJORITY,
        (SignalAction.BUY, SignalAction.SELL),
        (None, None),
        SignalAction.HOLD,
        Decimal("0.3"),
        Decimal("-0.3"),
    ) == (SignalAction.HOLD, Decimal("0"))
