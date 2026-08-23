from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.generation import (
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
    GenerationSourceType,
    StrategyGenerationRequest,
    StrategyValidationReport,
)
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.protocol import Strategy
from crypto_lab.domain.strategy.provenance import (
    StrategyGenerationProvenance,
    StrategySourceSnapshot,
)
from crypto_lab.domain.strategy.version import SemanticVersion


class NormalizedDatasetReader(Protocol):
    async def get_strategy_context(self, dataset_id: str) -> StrategyContext | None: ...


class StrategyDefinitionRepository(Protocol):
    async def get(self, definition_id: UUID) -> StrategyDefinition | None: ...

    async def create_or_resolve(self, definition: StrategyDefinition) -> StrategyDefinition: ...


class StrategyResolver(Protocol):
    def resolve(self, strategy_id: str, strategy_version: SemanticVersion) -> Strategy: ...


class ModelCandidate(Protocol):
    normalized_name: str
    display_name: str
    description: str
    structured_rules: Mapping[str, object]
    parameter_schema: ParameterSchema
    assumptions: tuple[str, ...]
    evidence: tuple[object, ...]
    source_code: str


class StrategyGenerationModel(Protocol):
    provider: str
    model_id: str
    model_version: str
    prompt_template_version: str

    async def generate(
        self, source_type: GenerationSourceType, inert_content: str, request_id: str
    ) -> Sequence[ModelCandidate]: ...


class StrategySourceReader(Protocol):
    async def prepare(self, url: str, request_id: str) -> tuple[StrategySourceSnapshot, str]: ...


class GeneratedArtifactStore(Protocol):
    async def put(self, artifact: GeneratedStrategyArtifact) -> str: ...

    async def get(self, content_reference: str) -> GeneratedStrategyArtifact: ...


class GeneratedStrategyValidationRuntime(Protocol):
    policy_version: str

    async def validate(self, artifact: GeneratedStrategyArtifact) -> StrategyValidationReport: ...


class StrategyGenerationRepository(Protocol):
    async def save_request(self, request: StrategyGenerationRequest) -> None: ...

    async def save_source(self, source: StrategySourceSnapshot) -> None: ...

    async def save_draft(self, draft: GeneratedStrategyDraft) -> GeneratedStrategyDraft: ...

    async def save_artifact(
        self, artifact: GeneratedStrategyArtifact, reference: str
    ) -> GeneratedStrategyArtifact: ...

    async def save_report(self, report: StrategyValidationReport) -> None: ...

    async def get_request(self, request_id: UUID) -> StrategyGenerationRequest | None: ...

    async def get_draft(self, draft_id: UUID) -> GeneratedStrategyDraft | None: ...

    async def list_drafts(self, request_id: UUID) -> tuple[GeneratedStrategyDraft, ...]: ...

    async def get_source(self, source_id: UUID) -> StrategySourceSnapshot | None: ...

    async def get_artifact(self, artifact_id: UUID) -> GeneratedStrategyArtifact | None: ...

    async def get_report(self, report_id: UUID) -> StrategyValidationReport | None: ...

    async def find_report(
        self, artifact_id: UUID, policy_version: str
    ) -> StrategyValidationReport | None: ...

    async def activate(
        self, draft: GeneratedStrategyDraft, provenance: StrategyGenerationProvenance
    ) -> None: ...

    async def list_activated(self) -> tuple[StrategyGenerationProvenance, ...]: ...

    async def find_activated_by_content(
        self, strategy_id: str, artifact_fingerprint: str
    ) -> StrategyGenerationProvenance | None: ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...
