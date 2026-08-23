from __future__ import annotations

from collections.abc import Awaitable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.parameters import ParameterSchema, ValidatedParameterSet
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult
from crypto_lab.domain.strategy.version import SemanticVersion


class StrategyCapability(StrEnum):
    STRENGTH = "STRENGTH"
    REASON = "REASON"


@dataclass(frozen=True, slots=True)
class StrategyMetadata:
    strategy_id: str
    strategy_type: str
    display_name: str
    strategy_version: SemanticVersion
    contract_version: SemanticVersion
    parameter_schema: ParameterSchema
    capabilities: frozenset[StrategyCapability] = frozenset()
    origin: StrategyOrigin = StrategyOrigin.BUILT_IN
    generation_provenance_id: UUID | None = None
    generated_artifact_fingerprint: str | None = None

    def __post_init__(self) -> None:
        generated = self.origin is StrategyOrigin.LLM_GENERATED
        has_references = (
            self.generation_provenance_id is not None
            and self.generated_artifact_fingerprint is not None
        )
        if generated != has_references:
            raise ValueError("generated metadata requires safe immutable provenance references")


class Strategy(Protocol):
    @property
    def metadata(self) -> StrategyMetadata: ...

    def validate_parameters(self, raw: Mapping[str, object]) -> ValidatedParameterSet: ...

    def analyze(
        self, definition: StrategyDefinition, context: StrategyContext
    ) -> StrategyAnalysisResult | Awaitable[StrategyAnalysisResult]: ...
