from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Path, Request

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.strategy_generation import (
    ActivateGeneratedStrategyRequest,
    CreateStrategyGenerationRequest,
    GeneratedDraftDto,
    GenerationRequestDto,
    generated_draft_dto,
    request_dto,
)
from crypto_lab.application.strategies.activate_generated_strategy import (
    ActivateGeneratedStrategyCommand,
)
from crypto_lab.application.strategies.generate_strategies import GenerateStrategiesCommand
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError

router = APIRouter(prefix="/api/v1", tags=["strategy-generation"])


@router.post(
    "/strategy-generation-requests",
    response_model=SuccessEnvelope[GenerationRequestDto],
    status_code=202,
)
async def create_generation_request(
    request: Request,
    body: CreateStrategyGenerationRequest,
    background_tasks: BackgroundTasks,
) -> SuccessEnvelope[GenerationRequestDto]:
    use_case = request.app.state.container.strategy_generation
    if use_case is None:
        raise StrategyError(
            ErrorCategory.GENERATION_FAILED,
            "strategy generation is not configured",
        )
    generated = await use_case.submit(
        GenerateStrategiesCommand(body.source_type, body.submitted_value)
    )
    background_tasks.add_task(use_case.process, generated)
    return success_envelope(
        request_dto(generated, ()),
        "Strategy generation accepted; poll the request for reviewable drafts.",
        request_id(request),
    )


@router.get(
    "/strategy-generation-requests/{requestId}",
    response_model=SuccessEnvelope[GenerationRequestDto],
)
async def get_generation_request(
    request: Request, request_identity: UUID = Path(alias="requestId")
) -> SuccessEnvelope[GenerationRequestDto]:
    repository = request.app.state.container.strategy_generation_repository
    if repository is None:
        raise StrategyError(
            ErrorCategory.GENERATION_FAILED, "strategy generation is not configured"
        )
    generated = await repository.get_request(request_identity)
    if generated is None:
        raise StrategyError(
            ErrorCategory.STRATEGY_INTENT_UNRESOLVED, "generation request not found"
        )
    drafts = await repository.list_drafts(request_identity)
    return success_envelope(
        request_dto(generated, drafts), "Generation request loaded.", request_id(request)
    )


@router.get(
    "/strategy-generation-drafts/{draftId}",
    response_model=SuccessEnvelope[GeneratedDraftDto],
)
async def get_generation_draft(
    request: Request, draft_identity: UUID = Path(alias="draftId")
) -> SuccessEnvelope[GeneratedDraftDto]:
    repository = request.app.state.container.strategy_generation_repository
    if repository is None:
        raise StrategyError(
            ErrorCategory.GENERATION_FAILED, "strategy generation is not configured"
        )
    draft = await repository.get_draft(draft_identity)
    if draft is None:
        raise StrategyError(ErrorCategory.STRATEGY_INTENT_UNRESOLVED, "generation draft not found")
    source = await repository.get_source(draft.source_snapshot_id)
    report = (
        await repository.get_report(draft.validation_report_id)
        if draft.validation_report_id
        else None
    )
    if source is None:
        raise StrategyError(ErrorCategory.GENERATION_FAILED, "draft provenance is unavailable")
    return success_envelope(
        generated_draft_dto(draft, source, report), "Draft loaded.", request_id(request)
    )


@router.post(
    "/strategy-generation-drafts/{draftId}/activate",
    response_model=SuccessEnvelope[dict[str, str]],
)
async def activate_generation_draft(
    request: Request,
    body: ActivateGeneratedStrategyRequest,
    draft_identity: UUID = Path(alias="draftId"),
) -> SuccessEnvelope[dict[str, str]]:
    use_case = request.app.state.container.strategy_activation
    if use_case is None:
        raise StrategyError(
            ErrorCategory.GENERATION_FAILED, "strategy generation is not configured"
        )
    provenance = await use_case.execute(
        ActivateGeneratedStrategyCommand(
            draft_identity,
            body.draft_fingerprint,
            body.artifact_fingerprint,
            body.validation_report_id,
            body.confirmed,
        )
    )
    return success_envelope(
        {
            "strategyId": provenance.strategy_id,
            "strategyVersion": provenance.strategy_version,
            "provenanceId": str(provenance.id),
        },
        "Generated strategy activated and available for reuse.",
        request_id(request),
    )
