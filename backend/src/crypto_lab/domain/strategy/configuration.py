from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc
from crypto_lab.domain.strategy.signal import SignalAction


def _decimal(value: Decimal) -> str:
    return canonical_decimal(value)


class StrategyConfigurationKind(StrEnum):
    SINGLE = "SINGLE"
    COMPOSITE = "COMPOSITE"


class CombinationMethod(StrEnum):
    MAJORITY = "MAJORITY"
    WEIGHTED = "WEIGHTED"


@dataclass(frozen=True, slots=True)
class StrategyConfigurationSelection:
    provider: str
    pair: str
    timeframe: Timeframe

    def __post_init__(self) -> None:
        if not self.provider or self.provider.upper() != self.provider:
            raise ValueError("provider must be an uppercase stable identifier")
        if not self.pair or self.pair.upper() != self.pair:
            raise ValueError("pair must be an uppercase stable identifier")


@dataclass(frozen=True, slots=True)
class StrategyConfigurationMember:
    strategy_id: str
    strategy_version: str
    definition_id: UUID
    definition_fingerprint: str
    parameters: dict[str, str | int]
    weight: Decimal | None = None

    def __post_init__(self) -> None:
        if len(self.definition_fingerprint) != 64:
            raise ValueError("member definition fingerprint must be SHA-256")
        if self.weight is not None and (not self.weight.is_finite() or self.weight < 0):
            raise ValueError("member weight must be finite and non-negative")
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class StrategyCombinationRule:
    method: CombinationMethod
    tie_action: SignalAction = SignalAction.HOLD
    buy_threshold: Decimal = Decimal("0.3")
    sell_threshold: Decimal = Decimal("-0.3")

    def __post_init__(self) -> None:
        if not self.buy_threshold.is_finite() or not self.sell_threshold.is_finite():
            raise ValueError("combination thresholds must be finite")
        if self.sell_threshold >= self.buy_threshold:
            raise ValueError("sell threshold must be below buy threshold")


@dataclass(frozen=True, slots=True)
class SavedStrategyConfiguration:
    id: UUID
    configuration_key: str
    configuration_version: int
    display_name: str
    kind: StrategyConfigurationKind
    root_definition_id: UUID
    selection: StrategyConfigurationSelection
    members: tuple[StrategyConfigurationMember, ...]
    combination: StrategyCombinationRule | None
    created_at: datetime

    def __post_init__(self) -> None:
        require_utc(self.created_at)
        if not self.configuration_key or self.configuration_version < 1 or not self.display_name:
            raise ValueError("configuration identity, version and display name are required")
        if self.kind is StrategyConfigurationKind.SINGLE:
            if len(self.members) != 1 or self.combination is not None:
                raise ValueError(
                    "single configurations require exactly one member and no combination"
                )
            if self.root_definition_id != self.members[0].definition_id:
                raise ValueError("single root definition must be its member definition")
        else:
            if not 2 <= len(self.members) <= 4 or self.combination is None:
                raise ValueError("composite configurations require two to four members and a rule")
            if self.combination.method is CombinationMethod.WEIGHTED:
                weights = tuple(member.weight for member in self.members)
                if any(weight is None for weight in weights):
                    raise ValueError("weighted composites require every member weight")
                if sum((weight or Decimal(0)) for weight in weights) != Decimal("1"):
                    raise ValueError("weighted composite weights must sum exactly to 1")

    @property
    def content_fingerprint(self) -> str:
        payload = {
            "combination": None
            if self.combination is None
            else {
                "buyThreshold": _decimal(self.combination.buy_threshold),
                "method": self.combination.method.value,
                "sellThreshold": _decimal(self.combination.sell_threshold),
                "tieAction": self.combination.tie_action.value,
            },
            "displayName": self.display_name,
            "kind": self.kind.value,
            "members": [
                {
                    "definitionFingerprint": member.definition_fingerprint,
                    "strategyId": member.strategy_id,
                    "strategyVersion": member.strategy_version,
                    "weight": None if member.weight is None else _decimal(member.weight),
                }
                for member in self.members
            ],
            "selection": {
                "pair": self.selection.pair,
                "provider": self.selection.provider,
                "timeframe": self.selection.timeframe.value,
            },
        }
        return hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
