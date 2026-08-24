from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.backtest_evaluation import (
    ComparisonDto,
    ComparisonRequest,
    CreateEvaluationRequest,
    EvaluationResultDto,
    comparison_to_dto,
    evaluation_to_dto,
)
from crypto_lab.domain.evaluation.comparison import ComparisonMode

router = APIRouter(prefix="/api/v1", tags=["evaluations"])


@router.post(
    "/evaluation-results",
    response_model=SuccessEnvelope[EvaluationResultDto],
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_backtest_result(
    request: Request, body: CreateEvaluationRequest
) -> SuccessEnvelope[EvaluationResultDto]:
    try:
        value = await request.app.state.container.evaluate_backtest.execute(
            body.backtest_result_id,
            body.evaluation_policy_id,
            body.evaluation_policy_version,
            body.scoring_policy_id,
            body.scoring_policy_version,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return success_envelope(evaluation_to_dto(value), "Evaluation completed.", request_id(request))


@router.get(
    "/evaluation-results/{evaluation_result_id}",
    response_model=SuccessEnvelope[EvaluationResultDto],
)
async def get_evaluation_result(
    request: Request, evaluation_result_id: UUID
) -> SuccessEnvelope[EvaluationResultDto]:
    value = await request.app.state.container.evaluation_repository.get(evaluation_result_id)
    if value is None:
        raise HTTPException(404, "Evaluation result not found")
    return success_envelope(evaluation_to_dto(value), "Evaluation loaded.", request_id(request))


@router.post("/evaluation-comparisons", response_model=SuccessEnvelope[ComparisonDto])
async def compare_evaluation_results(
    request: Request, body: ComparisonRequest
) -> SuccessEnvelope[ComparisonDto]:
    try:
        value = await request.app.state.container.compare_evaluations.execute(
            body.evaluation_result_ids, ComparisonMode(body.mode)
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return success_envelope(
        comparison_to_dto(value), "Evaluation comparison completed.", request_id(request)
    )
