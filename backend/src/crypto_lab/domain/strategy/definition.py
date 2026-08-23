from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis
from crypto_lab.domain.strategy.parameters import ValidatedParameterSet
from crypto_lab.domain.strategy.version import SemanticVersion


class StrategyOrigin(StrEnum):
    BUILT_IN = "BUILT_IN"
    LLM_GENERATED = "LLM_GENERATED"


@dataclass(frozen=True, slots=True)
class StrategyDefinition:
    id: UUID
    strategy_id: str
    strategy_type: str
    strategy_version: SemanticVersion
    contract_version: SemanticVersion
    parameters: ValidatedParameterSet
    created_at: datetime
    origin: StrategyOrigin = StrategyOrigin.BUILT_IN
    generated_artifact_id: UUID | None = None
    generation_provenance_id: UUID | None = None

    def __post_init__(self) -> None:
        if (
            not self.strategy_id
            or self.strategy_id.lower() != self.strategy_id
            or not self.strategy_type
        ):
            raise ValueError("strategy identity is invalid")
        if self.origin is StrategyOrigin.LLM_GENERATED and (
            self.generated_artifact_id is None or self.generation_provenance_id is None
        ):
            raise ValueError("generated definitions require artifact and provenance")
        if self.origin is StrategyOrigin.BUILT_IN and (
            self.generated_artifact_id is not None or self.generation_provenance_id is not None
        ):
            raise ValueError("built-in definitions cannot reference generated provenance")

    @property
    def content_fingerprint(self) -> str:
        values = {
            key: value if isinstance(value, int) else canonical_decimal(value)
            for key, value in self.parameters.values.items()
        }
        payload = {
            "contractVersion": str(self.contract_version),
            "generatedArtifactId": None
            if self.generated_artifact_id is None
            else str(self.generated_artifact_id),
            "generationProvenanceId": None
            if self.generation_provenance_id is None
            else str(self.generation_provenance_id),
            "origin": self.origin.value,
            "parameterSchemaFingerprint": self.parameters.schema_fingerprint,
            "parameters": values,
            "strategyId": self.strategy_id,
            "strategyType": self.strategy_type,
            "strategyVersion": str(self.strategy_version),
        }
        return hashlib.sha256(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()

    @property
    def created_at_text(self) -> str:
        return format_utc_millis(self.created_at)
