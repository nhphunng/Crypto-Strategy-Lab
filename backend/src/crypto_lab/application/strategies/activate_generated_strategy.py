from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, uuid4, uuid5

from crypto_lab.application.strategies.ports import (
    ClockPort,
    GeneratedArtifactStore,
    StrategyDefinitionRepository,
    StrategyGenerationModel,
    StrategyGenerationRepository,
)
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.generation import DraftStatus
from crypto_lab.domain.strategy.provenance import StrategyGenerationProvenance
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)
from crypto_lab.infrastructure.sandbox.isolated_generated_strategy import (
    IsolatedGeneratedStrategy,
)


@dataclass(frozen=True, slots=True)
class ActivateGeneratedStrategyCommand:
    draft_id: UUID
    draft_fingerprint: str
    artifact_fingerprint: str
    validation_report_id: UUID
    confirmed: bool
    confirmed_by: str = "workspace-analyst"


class ActivateGeneratedStrategy:
    policy_version = "generated-strategy-activation-v1"

    def __init__(
        self,
        repository: StrategyGenerationRepository,
        artifacts: GeneratedArtifactStore,
        registry: StrategyRegistry,
        runtime: DockerGeneratedStrategyRuntime,
        model: StrategyGenerationModel,
        clock: ClockPort,
        definitions: StrategyDefinitionRepository | None = None,
    ) -> None:
        self._repository = repository
        self._artifacts = artifacts
        self._registry = registry
        self._runtime = runtime
        self._model = model
        self._clock = clock
        self._definitions = definitions

    async def execute(
        self, command: ActivateGeneratedStrategyCommand
    ) -> StrategyGenerationProvenance:
        draft = await self._repository.get_draft(command.draft_id)
        if draft is None or not command.confirmed:
            raise _not_allowed("draft is unavailable or confirmation is absent")
        if draft.status is not DraftStatus.READY_FOR_CONFIRMATION:
            raise _not_allowed("draft is not ready for confirmation")
        if draft.draft_fingerprint != command.draft_fingerprint:
            raise _not_allowed("reviewed draft fingerprint does not match")
        if draft.generated_artifact_id is None or draft.validation_report_id is None:
            raise _not_allowed("draft lacks an artifact or validation report")
        artifact_metadata = await self._repository.get_artifact(draft.generated_artifact_id)
        report = await self._repository.get_report(command.validation_report_id)
        if artifact_metadata is None or report is None:
            raise _not_allowed("artifact or validation report is unavailable")
        if (
            report.id != draft.validation_report_id
            or report.artifact_id != artifact_metadata.id
            or report.artifact_fingerprint != command.artifact_fingerprint
            or artifact_metadata.content_fingerprint != command.artifact_fingerprint
            or report.policy_version != self._runtime.policy_version
            or not report.passed
        ):
            raise _not_allowed("artifact or current validation evidence does not match")
        stored_artifact = await self._artifacts.get(artifact_metadata.content_fingerprint)
        artifact = replace(
            stored_artifact,
            id=artifact_metadata.id,
            draft_id=artifact_metadata.draft_id,
        )
        existing = await self._repository.find_activated_by_content(
            draft.normalized_name, artifact.content_fingerprint
        )
        if existing is not None:
            now = self._clock.now()
            duplicate_link = StrategyGenerationProvenance(
                uuid4(),
                draft.generation_request_id,
                draft.source_snapshot_id,
                draft.id,
                existing.artifact_id,
                existing.validation_report_id,
                existing.strategy_id,
                existing.strategy_version,
                existing.model_provider,
                existing.model_id,
                existing.model_version,
                existing.prompt_template_version,
                existing.generated_at,
                now,
                command.confirmed_by,
                self.policy_version,
            )
            await self._repository.activate(draft, duplicate_link)
            return duplicate_link
        version = self._next_version(draft.normalized_name)
        now = self._clock.now()
        provenance = StrategyGenerationProvenance(
            uuid4(),
            draft.generation_request_id,
            draft.source_snapshot_id,
            draft.id,
            artifact.id,
            report.id,
            draft.normalized_name,
            str(version),
            self._model.provider,
            self._model.model_id,
            self._model.model_version,
            self._model.prompt_template_version,
            artifact.created_at,
            now,
            command.confirmed_by,
            self.policy_version,
        )
        strategy = IsolatedGeneratedStrategy(
            strategy_id=draft.normalized_name,
            display_name=draft.display_name,
            strategy_version=version,
            parameter_schema=draft.parameter_schema,
            artifact=artifact,
            runtime=self._runtime,
            generation_provenance_id=provenance.id,
        )
        definition = None
        if self._definitions is not None:
            try:
                default_parameters = draft.parameter_schema.validate({})
            except StrategyError as error:
                raise _not_allowed(
                    "generated strategy requires a complete default parameter set"
                ) from error
            definition = StrategyDefinition(
                id=uuid5(provenance.id, "default-definition"),
                strategy_id=draft.normalized_name,
                strategy_type="GENERATED",
                strategy_version=version,
                contract_version=artifact.contract_version,
                parameters=default_parameters,
                created_at=now,
                origin=StrategyOrigin.LLM_GENERATED,
                generated_artifact_id=artifact.id,
                generation_provenance_id=provenance.id,
            )
        # Provenance, draft-status, and the definition are written by the repository in
        # one transaction: activation can never leave the strategy ACTIVATED without a
        # definition, or a definition without an activated provenance record. The
        # in-memory registry is updated only after that commit succeeds.
        await self._repository.activate(draft, provenance, definition)
        self._registry.register(strategy)
        return provenance

    def _next_version(self, strategy_id: str) -> SemanticVersion:
        versions = [
            entry.strategy_version
            for entry in self._registry.discover(status=None)
            if entry.strategy_id == strategy_id
        ]
        if not versions:
            return SemanticVersion(1, 0, 0)
        latest = max(versions)
        return SemanticVersion(latest.major, latest.minor, latest.patch + 1)


def _not_allowed(message: str) -> StrategyError:
    return StrategyError(ErrorCategory.ACTIVATION_NOT_ALLOWED, message)
