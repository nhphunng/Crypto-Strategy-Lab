from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import Field

from crypto_lab.api.common import ApiModel, SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.application.search_service import search_run_payload

router = APIRouter(prefix="/api/v1", tags=["strategy-search"])


class CreateSearchRunRequest(ApiModel):
    dataset_id: UUID = Field(alias="datasetId")
    strategy_ids: tuple[str, ...] = Field(alias="strategyIds", min_length=2)
    minimum_size: int = Field(2, alias="minimumSize", ge=2, le=4)
    maximum_size: int = Field(4, alias="maximumSize", ge=2, le=4)
    candidate_limit: int = Field(100, alias="candidateLimit", ge=1, le=2000)
    timeout_seconds: int = Field(900, alias="timeoutSeconds", ge=1, le=7200)
    no_improvement_limit: int = Field(100, alias="noImprovementLimit", ge=1, le=2000)
    seed: int = 424242


class SearchRunDto(ApiModel):
    id: UUID
    type: str
    status: str
    dataset_id: UUID = Field(alias="datasetId")
    strategy_ids: list[str] = Field(alias="strategyIds")
    minimum_size: int = Field(alias="minimumSize")
    maximum_size: int = Field(alias="maximumSize")
    candidate_limit: int = Field(alias="candidateLimit")
    generated: int
    running: int
    succeeded: int
    failed: int
    top_score: str | None = Field(alias="topScore")
    top_candidate: str | None = Field(alias="topCandidate")
    current_candidate: str | None = Field(alias="currentCandidate")
    generator: str
    seed: int
    stop_reason: str | None = Field(alias="stopReason")
    failure_detail: str | None = Field(alias="failureDetail")
    created_at: str = Field(alias="createdAt")
    started_at: str | None = Field(alias="startedAt")
    completed_at: str | None = Field(alias="completedAt")


class SearchCandidateDto(ApiModel):
    id: UUID
    sequence: int
    display_name: str = Field(alias="displayName")
    members: list[dict[str, object]]
    status: str
    score: str | None
    backtest_run_id: UUID | None = Field(alias="backtestRunId")
    evaluation_result_id: UUID | None = Field(alias="evaluationResultId")
    failure_code: str | None = Field(alias="failureCode")


def dto(row: object) -> SearchRunDto:
    return SearchRunDto.model_validate(search_run_payload(row))


@router.post(
    "/search-runs",
    response_model=SuccessEnvelope[SearchRunDto],
    status_code=status.HTTP_201_CREATED,
)
async def create_search_run(
    request: Request, body: CreateSearchRunRequest
) -> SuccessEnvelope[SearchRunDto]:
    if body.minimum_size > body.maximum_size:
        raise HTTPException(
            422,
            {
                "code": "INVALID_COMBINATION_SIZE",
                "message": "minimumSize must not exceed maximumSize.",
            },
        )
    try:
        row = await request.app.state.container.strategy_search.create(
            dataset_id=body.dataset_id,
            strategy_ids=body.strategy_ids,
            minimum_size=body.minimum_size,
            maximum_size=body.maximum_size,
            candidate_limit=body.candidate_limit,
            timeout_seconds=body.timeout_seconds,
            no_improvement_limit=body.no_improvement_limit,
            seed=body.seed,
        )
    except ValueError as exc:
        raise HTTPException(
            422, {"code": "SEARCH_CONFIGURATION_INVALID", "message": str(exc)}
        ) from exc
    return success_envelope(dto(row), "Strategy search queued.", request_id(request))


@router.get("/search-runs", response_model=SuccessEnvelope[tuple[SearchRunDto, ...]])
async def list_search_runs(
    request: Request, limit: int = Query(100, ge=1, le=200)
) -> SuccessEnvelope[tuple[SearchRunDto, ...]]:
    rows = await request.app.state.container.search_repository.list(limit)
    return success_envelope(
        tuple(dto(row) for row in rows), "Strategy search runs loaded.", request_id(request)
    )


@router.get("/search-runs/{run_id}", response_model=SuccessEnvelope[SearchRunDto])
async def get_search_run(request: Request, run_id: UUID) -> SuccessEnvelope[SearchRunDto]:
    row = await request.app.state.container.search_repository.get(run_id)
    if row is None:
        raise HTTPException(
            404, {"code": "SEARCH_RUN_NOT_FOUND", "message": "Search run not found."}
        )
    return success_envelope(dto(row), "Strategy search run loaded.", request_id(request))


@router.post("/search-runs/{run_id}/cancel", response_model=SuccessEnvelope[SearchRunDto])
async def cancel_search_run(request: Request, run_id: UUID) -> SuccessEnvelope[SearchRunDto]:
    await request.app.state.container.strategy_search.cancel(run_id)
    row = await request.app.state.container.search_repository.get(run_id)
    if row is None:
        raise HTTPException(
            404, {"code": "SEARCH_RUN_NOT_FOUND", "message": "Search run not found."}
        )
    return success_envelope(dto(row), "Strategy search cancelled.", request_id(request))


@router.get(
    "/search-runs/{run_id}/candidates",
    response_model=SuccessEnvelope[tuple[SearchCandidateDto, ...]],
)
async def list_search_candidates(
    request: Request,
    run_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    sort: Literal["recent", "score"] = "recent",
) -> SuccessEnvelope[tuple[SearchCandidateDto, ...]]:
    rows = await request.app.state.container.search_repository.candidates(run_id, limit, sort)
    values = tuple(
        SearchCandidateDto(
            id=row.id,
            sequence=row.sequence,
            displayName=row.display_name,
            members=row.members,
            status=row.status,
            score=None if row.score is None else str(row.score),
            backtestRunId=row.backtest_run_id,
            evaluationResultId=row.evaluation_result_id,
            failureCode=row.failure_code,
        )
        for row in rows
    )
    return success_envelope(values, "Strategy search candidates loaded.", request_id(request))
