import pytest

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.registry import RegistryStatus, StrategyRegistry
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion


def test_registry_registers_resolves_and_discovers_deterministically() -> None:
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    strategy = MovingAverageStrategy()
    registry.register(strategy)
    assert registry.resolve("ma", SemanticVersion.parse("1.0.0")) is strategy
    assert [entry.strategy_id for entry in registry.discover()] == ["ma"]


def test_duplicate_and_batch_failure_are_atomic() -> None:
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    strategy = MovingAverageStrategy()
    registry.register(strategy)
    with pytest.raises(StrategyError) as caught:
        registry.register_many((strategy,))
    assert caught.value.category is ErrorCategory.DUPLICATE_STRATEGY_ENTRY
    assert len(registry.discover()) == 1


def test_exact_lifecycle_states_never_fallback() -> None:
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    strategy = MovingAverageStrategy()
    registry.register(strategy, RegistryStatus.DEPRECATED)
    with pytest.raises(StrategyError) as caught:
        registry.resolve("ma", SemanticVersion.parse("1.0.0"))
    assert caught.value.category is ErrorCategory.STRATEGY_VERSION_DEPRECATED
    with pytest.raises(StrategyError) as missing:
        registry.resolve("ma", SemanticVersion.parse("9.0.0"))
    assert missing.value.category is ErrorCategory.STRATEGY_VERSION_UNAVAILABLE
