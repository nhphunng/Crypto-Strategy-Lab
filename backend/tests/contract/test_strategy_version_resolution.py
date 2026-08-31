import pytest

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.registry import RegistryStatus, StrategyRegistry
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion


@pytest.mark.parametrize(
    ("status", "category"),
    (
        (RegistryStatus.DEPRECATED, ErrorCategory.STRATEGY_VERSION_DEPRECATED),
        (RegistryStatus.UNAVAILABLE, ErrorCategory.STRATEGY_VERSION_UNAVAILABLE),
    ),
)
def test_exact_version_states_are_distinct_and_never_fallback(status, category) -> None:
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    registry.register(MovingAverageStrategy(), status)
    with pytest.raises(StrategyError) as caught:
        registry.resolve("ma", SemanticVersion(1, 0, 0))
    assert caught.value.category is category
    with pytest.raises(StrategyError) as missing:
        registry.resolve("ma", SemanticVersion(1, 0, 1))
    assert missing.value.category is ErrorCategory.STRATEGY_VERSION_UNAVAILABLE
