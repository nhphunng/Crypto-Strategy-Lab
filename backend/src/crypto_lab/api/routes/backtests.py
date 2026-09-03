from __future__ import annotations

from uuid import UUID, uuid5

from fastapi import APIRouter, HTTPException, Query, Request, status

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.backtest_evaluation import (
    BacktestEvaluationPolicyBundleDto,
    BacktestResultDto,
    BacktestRunDto,
    CreateBacktestRunRequest,
    EquityPageDto,
    PageMetaDto,
    TradePageDto,
    equity_to_dto,
    policy_bundle_to_dto,
    result_to_dto,
    run_to_dto,
    trade_to_dto,
)
from crypto_lab.domain.backtest.configuration import BacktestConfiguration
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode

router = APIRouter(prefix="/api/v1", tags=["backtests"])


@router.get("/backtest-runs", response_model=SuccessEnvelope[tuple[BacktestRunDto, ...]])
async def list_backtest_runs(
    request: Request, limit: int = Query(100, ge=1, le=200)
) -> SuccessEnvelope[tuple[BacktestRunDto, ...]]:
    runs = await request.app.state.container.backtest_repository.list_runs(limit)
    search_repository = getattr(request.app.state.container, "search_repository", None)
    links = (
        await search_repository.candidate_links(tuple(run.configuration.run_id for run in runs))
        if search_repository is not None
        else {}
    )
    # Public queue terminology is consistent with the Runs UI while the immutable
    # domain record retains its original REQUESTED state.
    values = []
    for run in runs:
        value = run_to_dto(run)
        if value.status == "REQUESTED":
            value = value.model_copy(update={"status": "QUEUED"})
        link = links.get(run.configuration.run_id)
        if link is not None:
            value = value.model_copy(
                update={
                    "parent_search_run_id": link[0],
                    "candidate_display_name": link[1],
                }
            )
        values.append(value)
    return success_envelope(tuple(values), "Backtest runs loaded.", request_id(request))


@router.get(
    "/backtest-evaluation/policies",
    response_model=SuccessEnvelope[BacktestEvaluationPolicyBundleDto],
)
async def get_backtest_evaluation_policies(
    request: Request,
) -> SuccessEnvelope[BacktestEvaluationPolicyBundleDto]:
    from crypto_lab.api.dependencies import (
        BALANCED_SCORING_POLICY,
        EVALUATION_POLICY,
        EXECUTION_POLICY,
    )

    return success_envelope(
        policy_bundle_to_dto(EXECUTION_POLICY, EVALUATION_POLICY, BALANCED_SCORING_POLICY),
        "Backtest and Evaluation policies loaded.",
        request_id(request),
    )


@router.post(
    "/backtest-runs",
    response_model=SuccessEnvelope[BacktestRunDto],
    status_code=status.HTTP_201_CREATED,
)
async def create_backtest_run(
    request: Request, body: CreateBacktestRunRequest
) -> SuccessEnvelope[BacktestRunDto]:
    container = request.app.state.container
    dataset = await container.backtest_datasets.get_complete(body.dataset_id)
    if dataset is None:
        raise BacktestError(BacktestErrorCode.DATASET_INELIGIBLE, "complete dataset is unavailable")
    if (
        dataset.metadata.schema_version != body.dataset_schema_version
        or dataset.metadata.checksum != body.dataset_checksum
    ):
        raise BacktestError(
            BacktestErrorCode.DATASET_INTEGRITY_FAILED, "dataset identity or checksum differs"
        )
    analysis = await container.backtest_strategy_analyzer.analyze(
        body.strategy_definition_id, body.dataset_id, request_id(request)
    )
    definition, provenance = analysis.strategy_definition, analysis.context_provenance
    if (
        str(definition.strategy_version) != body.strategy_version
        or str(analysis.contract_version) != body.contract_version
    ):
        raise BacktestError(
            BacktestErrorCode.STRATEGY_INCOMPATIBLE, "strategy or contract version differs"
        )
    metadata = dataset.metadata
    configuration = BacktestConfiguration(
        uuid5(body.job_id, "run"),
        body.job_id,
        body.dataset_id,
        body.dataset_schema_version,
        body.dataset_checksum,
        metadata.selection.provider,
        metadata.selection.pair,
        metadata.selection.timeframe,
        metadata.time_range.start_time,
        metadata.time_range.end_time,
        body.strategy_definition_id,
        definition.strategy_id,
        body.strategy_version,
        body.contract_version,
        definition.parameters.canonical_fingerprint,
        provenance.context_fingerprint,
        body.execution_policy_id,
        body.execution_policy_version,
        body.initial_capital,
        body.fee_rate,
        body.slippage_rate,
        body.random_seed,
        sentiment_provenance=provenance.sentiment,
    )
    run = await container.create_backtest.execute(configuration)
    return success_envelope(run_to_dto(run), "Backtest run created.", request_id(request))


@router.post("/backtest-runs/{run_id}/start", response_model=SuccessEnvelope[BacktestResultDto])
async def start_backtest_run(request: Request, run_id: UUID) -> SuccessEnvelope[BacktestResultDto]:
    result = await request.app.state.container.execute_backtest.execute(run_id, request_id(request))
    return success_envelope(result_to_dto(result), "Backtest completed.", request_id(request))


@router.get("/backtest-runs/{run_id}", response_model=SuccessEnvelope[BacktestRunDto])
async def get_backtest_run(request: Request, run_id: UUID) -> SuccessEnvelope[BacktestRunDto]:
    run = await request.app.state.container.backtest_repository.get_run(run_id)
    if run is None:
        raise HTTPException(
            404,
            {
                "code": "BACKTEST_RUN_NOT_FOUND",
                "message": "Backtest run not found.",
            },
        )
    return success_envelope(run_to_dto(run), "Backtest run loaded.", request_id(request))


@router.get("/backtest-results/{result_id}", response_model=SuccessEnvelope[BacktestResultDto])
async def get_backtest_result(
    request: Request, result_id: UUID
) -> SuccessEnvelope[BacktestResultDto]:
    result = await request.app.state.container.get_backtest.get(result_id)
    if result is None:
        raise HTTPException(
            404,
            {
                "code": "BACKTEST_RESULT_NOT_FOUND",
                "message": "Backtest result not found.",
            },
        )
    return success_envelope(result_to_dto(result), "Backtest result loaded.", request_id(request))


@router.get("/backtest-results/{result_id}/trades", response_model=SuccessEnvelope[TradePageDto])
async def list_backtest_trades(
    request: Request,
    result_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=200),
) -> SuccessEnvelope[TradePageDto]:
    counts = await request.app.state.container.get_backtest.counts(result_id)
    if counts is None:
        raise HTTPException(
            404,
            {
                "code": "BACKTEST_RESULT_NOT_FOUND",
                "message": "Backtest result not found.",
            },
        )
    items, next_cursor = await request.app.state.container.get_backtest.trades(
        result_id, str((page - 1) * page_size), page_size
    )
    return success_envelope(
        TradePageDto(
            items=tuple(trade_to_dto(item) for item in items),
            pagination=PageMetaDto(page=page, page_size=page_size, total=counts[0]),
            next_cursor=next_cursor,
        ),
        "Backtest trades loaded.",
        request_id(request),
    )


@router.get(
    "/backtest-results/{result_id}/equity-curve", response_model=SuccessEnvelope[EquityPageDto]
)
async def list_backtest_equity(
    request: Request,
    result_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=200),
) -> SuccessEnvelope[EquityPageDto]:
    counts = await request.app.state.container.get_backtest.counts(result_id)
    if counts is None:
        raise HTTPException(
            404,
            {
                "code": "BACKTEST_RESULT_NOT_FOUND",
                "message": "Backtest result not found.",
            },
        )
    items, next_cursor = await request.app.state.container.get_backtest.equity(
        result_id, str((page - 1) * page_size), page_size
    )
    return success_envelope(
        EquityPageDto(
            items=tuple(equity_to_dto(item) for item in items),
            pagination=PageMetaDto(page=page, page_size=page_size, total=counts[1]),
            next_cursor=next_cursor,
        ),
        "Backtest equity loaded.",
        request_id(request),
    )
