from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from typing import cast
from uuid import UUID, uuid4, uuid5

from crypto_lab.application.strategies.ports import (
    ClockPort,
    GeneratedArtifactStore,
    GeneratedStrategyValidationRuntime,
    StrategyGenerationModel,
    StrategyGenerationRepository,
    StrategySourceReader,
)
from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError
from crypto_lab.domain.strategy.generation import (
    DraftStatus,
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
    GenerationRequestStatus,
    GenerationSourceType,
    RuleEvidence,
    StrategyGenerationRequest,
)
from crypto_lab.domain.strategy.provenance import RetentionClass, StrategySourceSnapshot
from crypto_lab.domain.strategy.version import SemanticVersion


@dataclass(frozen=True, slots=True)
class GenerateStrategiesCommand:
    source_type: GenerationSourceType
    submitted_value: str
    request_id: UUID | None = None


class GenerateStrategies:
    def __init__(
        self,
        model: StrategyGenerationModel,
        sources: StrategySourceReader,
        artifacts: GeneratedArtifactStore,
        validator: GeneratedStrategyValidationRuntime,
        repository: StrategyGenerationRepository,
        clock: ClockPort,
    ) -> None:
        self._model = model
        self._sources = sources
        self._artifacts = artifacts
        self._validator = validator
        self._repository = repository
        self._clock = clock

    async def execute(
        self, command: GenerateStrategiesCommand
    ) -> tuple[StrategyGenerationRequest, tuple[GeneratedStrategyDraft, ...]]:
        request = await self.submit(command)
        return await self.process(request)

    async def submit(self, command: GenerateStrategiesCommand) -> StrategyGenerationRequest:
        if command.request_id is not None:
            getter = getattr(self._repository, "get_request", None)
            existing = cast(
                StrategyGenerationRequest | None,
                await getter(command.request_id) if getter is not None else None,
            )
            if existing is not None:
                if (
                    existing.source_type is not command.source_type
                    or existing.submitted_value != command.submitted_value
                ):
                    raise StrategyError(
                        ErrorCategory.GENERATION_FAILED,
                        "request identity is already bound to different generation input",
                    )
                return existing
        now = self._clock.now()
        request = StrategyGenerationRequest(
            command.request_id or uuid4(),
            command.source_type,
            command.submitted_value,
            GenerationRequestStatus.RECEIVED,
            now,
            now,
        )
        await self._repository.save_request(request)
        return request

    async def process(
        self, request: StrategyGenerationRequest
    ) -> tuple[StrategyGenerationRequest, tuple[GeneratedStrategyDraft, ...]]:
        if request.status is GenerationRequestStatus.COMPLETED:
            return request, await self._list_drafts(request.id)
        try:
            request = replace(
                request,
                status=GenerationRequestStatus.SOURCE_PREPARING,
                updated_at=self._clock.now(),
            )
            await self._repository.save_request(request)
            source, inert_content = await self._prepare_source(request)
            await self._repository.save_source(source)
            request = replace(
                request,
                source_snapshot_id=source.id,
                status=GenerationRequestStatus.GENERATING,
                updated_at=self._clock.now(),
            )
            await self._repository.save_request(request)
            candidates = await self._model.generate(
                request.source_type, inert_content, str(request.id)
            )
            if request.source_type is GenerationSourceType.STRATEGY_NAME and len(candidates) != 1:
                raise StrategyError(
                    ErrorCategory.STRATEGY_INTENT_UNRESOLVED,
                    "strategy name could not be resolved to exactly one trading concept",
                )
            existing_drafts = {
                draft.candidate_index: draft for draft in await self._list_drafts(request.id)
            }
            drafts: list[GeneratedStrategyDraft] = []
            for index, candidate in enumerate(candidates):
                evidence = tuple(
                    item
                    if isinstance(item, RuleEvidence)
                    else RuleEvidence(str(index), str(item), None, True)
                    for item in candidate.evidence
                )
                draft = existing_drafts.get(index) or GeneratedStrategyDraft(
                    uuid5(request.id, f"candidate:{index}"),
                    request.id,
                    source.id,
                    index,
                    candidate.normalized_name,
                    candidate.display_name,
                    candidate.description,
                    candidate.structured_rules,
                    candidate.parameter_schema,
                    candidate.assumptions,
                    evidence,
                )
                if (
                    draft.generated_artifact_id is not None
                    and draft.validation_report_id is not None
                ):
                    drafts.append(draft)
                    continue
                draft = await self._repository.save_draft(draft)
                try:
                    artifact = GeneratedStrategyArtifact.create(
                        id=uuid5(draft.id, "artifact"),
                        draft_id=draft.id,
                        source_code=candidate.source_code,
                        contract_version=SemanticVersion.parse("1.0.0"),
                        declared_imports=_declared_imports(candidate.source_code),
                        capabilities=frozenset({"REASON"}),
                        created_at=self._clock.now(),
                    )
                    reference = await self._artifacts.put(artifact)
                    artifact = await self._repository.save_artifact(artifact, reference)
                    finder = getattr(self._repository, "find_report", None)
                    report = (
                        await finder(artifact.id, self._validator.policy_version)
                        if finder is not None
                        else None
                    )
                    if report is None:
                        report = await self._validator.validate(artifact)
                    await self._repository.save_report(report)
                    status = (
                        DraftStatus.READY_FOR_CONFIRMATION
                        if report.passed
                        else DraftStatus.VALIDATION_FAILED
                    )
                    draft = replace(
                        draft,
                        generated_artifact_id=artifact.id,
                        validation_report_id=report.id,
                        status=status,
                    )
                except Exception as error:
                    draft = replace(
                        draft,
                        status=DraftStatus.VALIDATION_FAILED,
                        failure_issues=(
                            ErrorIssue(
                                "candidate",
                                "CANDIDATE_PROCESSING_FAILED",
                                f"candidate failed safely during {type(error).__name__}",
                            ),
                        ),
                    )
                await self._repository.save_draft(draft)
                drafts.append(draft)
            request = replace(
                request, status=GenerationRequestStatus.COMPLETED, updated_at=self._clock.now()
            )
            await self._repository.save_request(request)
            return request, tuple(drafts)
        except Exception:
            request = replace(
                request, status=GenerationRequestStatus.FAILED, updated_at=self._clock.now()
            )
            await self._repository.save_request(request)
            raise

    async def _prepare_source(
        self, request: StrategyGenerationRequest
    ) -> tuple[StrategySourceSnapshot, str]:
        if request.source_type is GenerationSourceType.WEBPAGE_URL:
            return await self._sources.prepare(request.submitted_value, str(request.id))
        content = request.submitted_value.strip()
        snapshot = StrategySourceSnapshot(
            id=uuid5(request.id, "source"),
            source_type=request.source_type,
            content_fingerprint=StrategySourceSnapshot.fingerprint(content),
            access_policy_version="source-access-v1",
            retention_class=RetentionClass.FINGERPRINT_ONLY,
            size=len(content.encode()),
            media_type="text/plain",
        )
        return snapshot, content

    async def _list_drafts(self, request_id: UUID) -> tuple[GeneratedStrategyDraft, ...]:
        getter = getattr(self._repository, "list_drafts", None)
        if getter is None:
            return ()
        return cast(tuple[GeneratedStrategyDraft, ...], await getter(request_id))


def _declared_imports(source_code: str) -> frozenset[str]:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return frozenset()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".")[0])
    return frozenset(imports)
