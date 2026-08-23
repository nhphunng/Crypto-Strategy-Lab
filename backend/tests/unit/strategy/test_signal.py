from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from crypto_lab.domain.strategy.signal import Signal, SignalAction, SignalPhase
from crypto_lab.domain.strategy.version import SemanticVersion


def make_signal(sequence: int = 0) -> Signal:
    return Signal.create(
        strategy_definition_id=UUID("00000000-0000-0000-0000-000000000001"),
        strategy_id="ma",
        strategy_type="MA",
        strategy_version=SemanticVersion.parse("1.0.0"),
        contract_version=SemanticVersion.parse("1.0.0"),
        dataset_id="fixture",
        dataset_version="v1",
        context_fingerprint="a" * 64,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        sequence=sequence,
        action=SignalAction.HOLD,
        phase=SignalPhase.WARMUP,
        strength=Decimal("0"),
        reason="insufficient_history",
    )


def test_signal_identity_is_deterministic_and_value_is_immutable() -> None:
    assert make_signal().id == make_signal().id
    assert make_signal().id != make_signal(1).id
    with pytest.raises(AttributeError):
        make_signal().action = SignalAction.BUY  # type: ignore[misc]


def test_signal_rejects_invalid_sequence_or_non_finite_strength() -> None:
    with pytest.raises(ValueError):
        make_signal(-1)
