from __future__ import annotations

import logging

from crypto_lab.domain.strategy.implementations.bollinger import BollingerBandsStrategy
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.domain.strategy.implementations.rsi import RsiStrategy
from crypto_lab.domain.strategy.implementations.support_resistance import (
    SupportResistanceStrategy,
)
from crypto_lab.domain.strategy.protocol import Strategy
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.version import ContractVersionRange

logger = logging.getLogger(__name__)


def build_strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry(ContractVersionRange(major=1, minimum_minor=0, maximum_minor=0))
    strategies: tuple[Strategy, ...] = (
        BollingerBandsStrategy(),
        MovingAverageStrategy(),
        RsiStrategy(),
        SupportResistanceStrategy(),
    )
    registry.register_many(strategies)
    for entry in registry.discover():
        logger.info(
            "strategy_registered",
            extra={
                "strategy_id": entry.strategy_id,
                "strategy_version": str(entry.strategy_version),
                "contract_version": str(entry.metadata.contract_version),
                "status": entry.status.value,
            },
        )
    return registry
