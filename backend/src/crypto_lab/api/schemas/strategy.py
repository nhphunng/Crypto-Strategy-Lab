from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from crypto_lab.api.common import ApiModel
from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis
from crypto_lab.domain.strategy.parameters import ParameterDefinition
from crypto_lab.domain.strategy.registry import StrategyRegistryEntry
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult


class ParameterDefinitionDto(ApiModel):
    name: str
    description: str
    value_type: str = Field(alias="valueType")
    default_value: str | int | None = Field(alias="defaultValue")
    minimum: str | int | None
    maximum: str | int | None
    required: bool


class StrategyMetadataDto(ApiModel):
    strategy_id: str = Field(alias="strategyId")
    strategy_type: str = Field(alias="strategyType")
    display_name: str = Field(alias="displayName")
    strategy_version: str = Field(alias="strategyVersion")
    contract_version: str = Field(alias="contractVersion")
    status: str
    capabilities: tuple[str, ...]
    origin: str
    generation_provenance_id: str | None = Field(alias="generationProvenanceId")
    generated_artifact_fingerprint: str | None = Field(alias="generatedArtifactFingerprint")
    parameters: tuple[ParameterDefinitionDto, ...]


class StrategyListDto(ApiModel):
    strategies: tuple[StrategyMetadataDto, ...]


class StrategyAnalysisRequest(ApiModel):
    strategy_definition_id: UUID = Field(alias="strategyDefinitionId")
    dataset_id: str = Field(alias="datasetId")
    supported_contract_major: int = Field(default=1, alias="supportedContractMajor")
    minimum_contract_minor: int = Field(default=0, alias="minimumContractMinor")
    maximum_contract_minor: int = Field(default=0, alias="maximumContractMinor")


class SignalDto(ApiModel):
    id: str
    timestamp: str
    sequence: int
    action: Literal["BUY", "SELL", "HOLD"]
    phase: Literal["WARMUP", "EVALUATED"]
    strength: str | None
    reason: str | None


class StrategyAnalysisDto(ApiModel):
    strategy_definition_id: str = Field(alias="strategyDefinitionId")
    strategy_id: str = Field(alias="strategyId")
    strategy_type: str = Field(alias="strategyType")
    strategy_version: str = Field(alias="strategyVersion")
    contract_version: str = Field(alias="contractVersion")
    dataset_id: str = Field(alias="datasetId")
    dataset_version: str = Field(alias="datasetVersion")
    context_fingerprint: str = Field(alias="contextFingerprint")
    history_state: str = Field(alias="historyState")
    signals: tuple[SignalDto, ...]


def metadata_to_dto(entry: StrategyRegistryEntry) -> StrategyMetadataDto:
    metadata = entry.metadata
    return StrategyMetadataDto(
        strategy_id=metadata.strategy_id,
        strategy_type=metadata.strategy_type,
        display_name=metadata.display_name,
        strategy_version=str(metadata.strategy_version),
        contract_version=str(metadata.contract_version),
        status=entry.status.value,
        capabilities=tuple(sorted(item.value for item in metadata.capabilities)),
        origin=metadata.origin.value,
        generation_provenance_id=(
            str(metadata.generation_provenance_id)
            if metadata.generation_provenance_id is not None
            else None
        ),
        generated_artifact_fingerprint=metadata.generated_artifact_fingerprint,
        parameters=tuple(_parameter_to_dto(item) for item in metadata.parameter_schema.definitions),
    )


def analysis_to_dto(result: StrategyAnalysisResult) -> StrategyAnalysisDto:
    definition = result.strategy_definition
    provenance = result.context_provenance
    return StrategyAnalysisDto(
        strategy_definition_id=str(definition.id),
        strategy_id=definition.strategy_id,
        strategy_type=definition.strategy_type,
        strategy_version=str(definition.strategy_version),
        contract_version=str(result.contract_version),
        dataset_id=provenance.dataset_id,
        dataset_version=provenance.dataset_version,
        context_fingerprint=provenance.context_fingerprint,
        history_state=result.history_state.value,
        signals=tuple(
            SignalDto(
                id=item.id,
                timestamp=format_utc_millis(item.timestamp),
                sequence=item.sequence,
                action=item.action.value,
                phase=item.phase.value,
                strength=canonical_decimal(item.strength) if item.strength is not None else None,
                reason=item.reason,
            )
            for item in result.signals
        ),
    )


def _parameter_to_dto(item: ParameterDefinition) -> ParameterDefinitionDto:
    return ParameterDefinitionDto(
        name=item.name,
        description=item.description,
        value_type=item.value_type.value,
        default_value=_scalar(item.default_value),
        minimum=_scalar(item.minimum),
        maximum=_scalar(item.maximum),
        required=item.required,
    )


def _scalar(value: object) -> str | int | None:
    if value is None or isinstance(value, int):
        return value
    return canonical_decimal(value)  # type: ignore[arg-type]
