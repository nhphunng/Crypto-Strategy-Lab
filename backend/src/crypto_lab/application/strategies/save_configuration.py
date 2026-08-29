from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.configuration import (
    CombinationMethod,
    SavedStrategyConfiguration,
    StrategyCombinationRule,
    StrategyConfigurationKind,
    StrategyConfigurationMember,
    StrategyConfigurationSelection,
)
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.signal import SignalAction
from crypto_lab.domain.strategy.version import SemanticVersion


@dataclass(frozen=True, slots=True)
class StrategyConfigurationMemberInput:
    strategy_id: str
    strategy_version: str
    parameters: Mapping[str, object]
    weight: Decimal | None


@dataclass(frozen=True, slots=True)
class StrategyCombinationInput:
    method: CombinationMethod
    tie_action: SignalAction
    buy_threshold: Decimal
    sell_threshold: Decimal


@dataclass(frozen=True, slots=True)
class SaveStrategyConfigurationCommand:
    display_name: str
    provider: str
    pair: str
    timeframe: str
    members: tuple[StrategyConfigurationMemberInput, ...]
    combination: StrategyCombinationInput | None


class DefinitionRepository(Protocol):
    async def create_or_resolve(self, definition: StrategyDefinition) -> StrategyDefinition: ...
    async def find_exact(
        self, strategy_id: str, strategy_version: SemanticVersion
    ) -> tuple[StrategyDefinition, ...]: ...


class ConfigurationRepository(Protocol):
    async def save(
        self, configuration: SavedStrategyConfiguration
    ) -> SavedStrategyConfiguration: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class SaveStrategyConfiguration:
    def __init__(
        self,
        registry: StrategyRegistry,
        definitions: DefinitionRepository,
        configurations: ConfigurationRepository,
        clock: Clock,
    ) -> None:
        self._registry = registry
        self._definitions = definitions
        self._configurations = configurations
        self._clock = clock

    async def execute(
        self, command: SaveStrategyConfigurationCommand
    ) -> SavedStrategyConfiguration:
        members: list[StrategyConfigurationMember] = []
        for item in command.members:
            version = SemanticVersion.parse(item.strategy_version)
            strategy = self._registry.resolve(item.strategy_id, version)
            metadata = strategy.metadata
            parameters = strategy.validate_parameters(item.parameters)
            artifact_id = None
            provenance_id = None
            if metadata.origin is StrategyOrigin.LLM_GENERATED:
                existing = await self._definitions.find_exact(item.strategy_id, version)
                source = next(
                    (
                        definition
                        for definition in existing
                        if definition.origin is StrategyOrigin.LLM_GENERATED
                    ),
                    None,
                )
                if source is None:
                    raise ValueError("activated generated strategy definition is unavailable")
                artifact_id = source.generated_artifact_id
                provenance_id = source.generation_provenance_id
                definition = await self._definitions.create_or_resolve(
                    StrategyDefinition(
                        id=uuid4(),
                        strategy_id=metadata.strategy_id,
                        strategy_type=metadata.strategy_type,
                        strategy_version=metadata.strategy_version,
                        contract_version=metadata.contract_version,
                        parameters=parameters,
                        created_at=self._clock.now(),
                        origin=metadata.origin,
                        generated_artifact_id=artifact_id,
                        generation_provenance_id=provenance_id,
                    )
                )
            else:
                definition = await self._definitions.create_or_resolve(
                    StrategyDefinition(
                        id=uuid4(),
                        strategy_id=metadata.strategy_id,
                        strategy_type=metadata.strategy_type,
                        strategy_version=metadata.strategy_version,
                        contract_version=metadata.contract_version,
                        parameters=parameters,
                        created_at=self._clock.now(),
                        origin=metadata.origin,
                    )
                )
            values = {
                key: value if isinstance(value, int) else canonical_decimal(value)
                for key, value in definition.parameters.values.items()
            }
            members.append(
                StrategyConfigurationMember(
                    strategy_id=definition.strategy_id,
                    strategy_version=str(definition.strategy_version),
                    definition_id=definition.id,
                    definition_fingerprint=definition.content_fingerprint,
                    parameters=values,
                    weight=item.weight,
                )
            )

        selection = StrategyConfigurationSelection(
            command.provider, command.pair, Timeframe(command.timeframe)
        )
        combination = (
            None
            if command.combination is None
            else StrategyCombinationRule(
                command.combination.method,
                command.combination.tie_action,
                command.combination.buy_threshold,
                command.combination.sell_threshold,
            )
        )
        kind = (
            StrategyConfigurationKind.SINGLE
            if len(members) == 1
            else StrategyConfigurationKind.COMPOSITE
        )
        key = _configuration_key(tuple(members), combination)
        provisional_root = (
            members[0].definition_id
            if kind is StrategyConfigurationKind.SINGLE
            else uuid4()
        )
        provisional = SavedStrategyConfiguration(
            id=uuid4(),
            configuration_key=key,
            configuration_version=1,
            display_name=command.display_name,
            kind=kind,
            root_definition_id=provisional_root,
            selection=selection,
            members=tuple(members),
            combination=combination,
            created_at=self._clock.now(),
        )
        if kind is StrategyConfigurationKind.COMPOSITE:
            empty = ParameterSchema(()).validate({})
            root = await self._definitions.create_or_resolve(
                StrategyDefinition(
                    id=provisional_root,
                    strategy_id=f"composite-{provisional.content_fingerprint[:54]}",
                    strategy_type="COMPOSITE",
                    strategy_version=SemanticVersion(1, 0, 0),
                    contract_version=SemanticVersion(1, 0, 0),
                    parameters=empty,
                    created_at=self._clock.now(),
                )
            )
            provisional = SavedStrategyConfiguration(
                id=provisional.id,
                configuration_key=provisional.configuration_key,
                configuration_version=provisional.configuration_version,
                display_name=provisional.display_name,
                kind=provisional.kind,
                root_definition_id=root.id,
                selection=provisional.selection,
                members=provisional.members,
                combination=provisional.combination,
                created_at=provisional.created_at,
            )
        return await self._configurations.save(provisional)


def _configuration_key(
    members: tuple[StrategyConfigurationMember, ...],
    combination: StrategyCombinationRule | None,
) -> str:
    payload = {
        "members": [
            {"strategyId": item.strategy_id, "strategyVersion": item.strategy_version}
            for item in members
        ],
        "method": None if combination is None else combination.method.value,
    }
    digest = hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    return f"cfg-{digest[:32]}"
