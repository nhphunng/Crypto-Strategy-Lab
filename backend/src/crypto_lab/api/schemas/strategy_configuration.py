from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictInt, StrictStr, model_validator

from crypto_lab.api.common import ApiModel
from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis
from crypto_lab.domain.strategy.configuration import SavedStrategyConfiguration


class ConfigurationSelectionDto(ApiModel):
    provider: str = Field(min_length=1, max_length=32)
    pair: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=16)


class SaveConfigurationMemberRequest(ApiModel):
    strategy_id: str = Field(alias="strategyId", min_length=1, max_length=64)
    strategy_version: str = Field(alias="strategyVersion", min_length=1, max_length=32)
    parameters: dict[str, StrictInt | StrictStr]
    weight: StrictStr | None = None


class SaveCombinationRequest(ApiModel):
    method: Literal["MAJORITY", "WEIGHTED"]
    tie_action: Literal["BUY", "SELL", "HOLD"] = Field(default="HOLD", alias="tieAction")
    buy_threshold: StrictStr = Field(default="0.3", alias="buyThreshold")
    sell_threshold: StrictStr = Field(default="-0.3", alias="sellThreshold")


class SaveStrategyConfigurationRequest(ApiModel):
    display_name: str = Field(alias="displayName", min_length=1, max_length=160)
    selection: ConfigurationSelectionDto
    members: tuple[SaveConfigurationMemberRequest, ...] = Field(min_length=1, max_length=4)
    combination: SaveCombinationRequest | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> SaveStrategyConfigurationRequest:
        if len(self.members) == 1 and self.combination is not None:
            raise ValueError("single configurations must not define combination rules")
        if len(self.members) > 1 and self.combination is None:
            raise ValueError("composite configurations require combination rules")
        if self.combination is not None and self.combination.method == "WEIGHTED":
            if any(member.weight is None for member in self.members):
                raise ValueError("weighted composites require every member weight")
            try:
                weights = tuple(Decimal(member.weight or "") for member in self.members)
            except InvalidOperation as exc:
                raise ValueError("weights must be exact decimal strings") from exc
            if any(not value.is_finite() or value < 0 for value in weights):
                raise ValueError("weights must be finite and non-negative")
            if sum(weights) != Decimal("1"):
                raise ValueError("weighted composite weights must sum exactly to 1")
        return self


class SavedConfigurationMemberDto(ApiModel):
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    definition_id: UUID = Field(alias="definitionId")
    parameters: dict[str, str | int]
    weight: str | None


class SavedCombinationDto(ApiModel):
    method: Literal["MAJORITY", "WEIGHTED"]
    tie_action: Literal["BUY", "SELL", "HOLD"] = Field(alias="tieAction")
    buy_threshold: str = Field(alias="buyThreshold")
    sell_threshold: str = Field(alias="sellThreshold")


class SavedStrategyConfigurationDto(ApiModel):
    configuration_id: UUID = Field(alias="configurationId")
    configuration_key: str = Field(alias="configurationKey")
    configuration_version: int = Field(alias="configurationVersion", ge=1)
    display_name: str = Field(alias="displayName")
    kind: Literal["SINGLE", "COMPOSITE"]
    root_definition_id: UUID = Field(alias="rootDefinitionId")
    selection: ConfigurationSelectionDto
    members: tuple[SavedConfigurationMemberDto, ...]
    combination: SavedCombinationDto | None
    content_fingerprint: str = Field(alias="contentFingerprint", pattern=r"^[0-9a-f]{64}$")
    created_at: str = Field(alias="createdAt")


class StrategyConfigurationListDto(ApiModel):
    configurations: tuple[SavedStrategyConfigurationDto, ...]


def configuration_to_dto(value: SavedStrategyConfiguration) -> SavedStrategyConfigurationDto:
    combination = value.combination
    return SavedStrategyConfigurationDto(
        configuration_id=value.id,
        configuration_key=value.configuration_key,
        configuration_version=value.configuration_version,
        display_name=value.display_name,
        kind=value.kind.value,
        root_definition_id=value.root_definition_id,
        selection=ConfigurationSelectionDto(
            provider=value.selection.provider,
            pair=value.selection.pair,
            timeframe=value.selection.timeframe.value,
        ),
        members=tuple(
            SavedConfigurationMemberDto(
                strategy_id=member.strategy_id,
                strategy_version=member.strategy_version,
                definition_id=member.definition_id,
                parameters=dict(member.parameters),
                weight=None if member.weight is None else canonical_decimal(member.weight),
            )
            for member in value.members
        ),
        combination=None
        if combination is None
        else SavedCombinationDto(
            method=combination.method.value,
            tie_action=combination.tie_action.value,
            buy_threshold=canonical_decimal(combination.buy_threshold),
            sell_threshold=canonical_decimal(combination.sell_threshold),
        ),
        content_fingerprint=value.content_fingerprint,
        created_at=format_utc_millis(value.created_at),
    )
