from datetime import UTC, datetime
from uuid import UUID

from crypto_lab.domain.strategy.provenance import StrategyGenerationProvenance


def test_generation_provenance_is_immutable_and_exact() -> None:
    value = StrategyGenerationProvenance(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        UUID(int=4),
        UUID(int=5),
        UUID(int=6),
        "generated",
        "1.0.0",
        "provider",
        "model",
        "version",
        "prompt-v1",
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
        "analyst",
        "activation-v1",
    )
    assert value.artifact_id == UUID(int=5)
    try:
        value.model_version = "changed"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("provenance must be immutable")
