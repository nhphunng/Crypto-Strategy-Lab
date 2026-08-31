from __future__ import annotations

from dataclasses import dataclass

from crypto_lab.domain.strategy.registry import (
    RegistryStatus,
    StrategyRegistry,
    StrategyRegistryEntry,
)
from crypto_lab.domain.strategy.version import SemanticVersion


@dataclass(slots=True)
class DiscoverStrategies:
    registry: StrategyRegistry

    def list(
        self, status: RegistryStatus | None = RegistryStatus.AVAILABLE
    ) -> tuple[StrategyRegistryEntry, ...]:
        return self.registry.discover(status)

    def get(self, strategy_id: str, version: str) -> StrategyRegistryEntry:
        return self.registry.metadata(strategy_id, SemanticVersion.parse(version))
