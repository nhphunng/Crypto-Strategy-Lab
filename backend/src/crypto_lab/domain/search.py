from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.strategy.parameters import ParameterValueType
from crypto_lab.domain.strategy.registry import RegistryStatus, StrategyRegistry


@dataclass(frozen=True, slots=True)
class CandidateMember:
    strategy_id: str
    strategy_version: str
    parameters: dict[str, str | int]


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    fingerprint: str
    display_name: str
    members: tuple[CandidateMember, ...]


class StrategyGenerator(Protocol):
    generator_id: str
    version: str

    def generate(
        self,
        strategy_ids: tuple[str, ...],
        minimum_size: int,
        maximum_size: int,
        limit: int,
        seed: int,
    ) -> Iterator[StrategyCandidate]: ...


class RandomSearchGenerator:
    """Deterministic, registry-driven candidate generator with run-local de-duplication."""

    generator_id = "random-search"
    version = "1.0.0"

    def __init__(self, registry: StrategyRegistry) -> None:
        self._registry = registry

    def generate(
        self,
        strategy_ids: tuple[str, ...],
        minimum_size: int,
        maximum_size: int,
        limit: int,
        seed: int,
    ) -> Iterator[StrategyCandidate]:
        available = {
            entry.strategy_id: entry
            for entry in self._registry.discover(RegistryStatus.AVAILABLE)
            if entry.strategy_id in strategy_ids
        }
        if len(available) < 2:
            raise ValueError("search requires at least two available strategies")
        low, high = max(2, minimum_size), min(4, maximum_size, len(available))
        if low > high:
            raise ValueError("combination size is incompatible with the search space")
        rng, seen = random.Random(seed), set[str]()
        attempts = 0
        while len(seen) < limit and attempts < max(100, limit * 50):
            attempts += 1
            chosen = sorted(rng.sample(tuple(available), rng.randint(low, high)))
            members = tuple(self._member(available[item], rng) for item in chosen)
            payload = [
                {
                    "strategyId": item.strategy_id,
                    "strategyVersion": item.strategy_version,
                    "parameters": item.parameters,
                }
                for item in members
            ]
            fingerprint = hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            yield StrategyCandidate(
                fingerprint,
                " + ".join(available[item].metadata.display_name for item in chosen),
                members,
            )

    @staticmethod
    def _member(entry: object, rng: random.Random) -> CandidateMember:
        metadata = entry.metadata  # type: ignore[attr-defined]
        values: dict[str, str | int] = {}
        for definition in metadata.parameter_schema.definitions:
            value: int | Decimal
            if definition.allowed_values:
                value = rng.choice(sorted(definition.allowed_values))
            elif definition.value_type is ParameterValueType.INTEGER:
                low = int(
                    definition.minimum
                    if definition.minimum is not None
                    else definition.default_value or 1
                )
                high = int(
                    definition.maximum
                    if definition.maximum is not None
                    else definition.default_value or low
                )
                # Wide schemas are sampled on a stable, useful grid instead of every integer.
                value = rng.randint(low, high)
            else:
                decimal_low = Decimal(
                    definition.minimum
                    if definition.minimum is not None
                    else definition.default_value or 0
                )
                decimal_high = Decimal(
                    definition.maximum
                    if definition.maximum is not None
                    else definition.default_value or decimal_low
                )
                value = decimal_low + (decimal_high - decimal_low) * Decimal(
                    rng.randrange(0, 101)
                ) / Decimal(100)
            values[definition.name] = value if isinstance(value, int) else canonical_decimal(value)
        return CandidateMember(metadata.strategy_id, str(metadata.strategy_version), values)
