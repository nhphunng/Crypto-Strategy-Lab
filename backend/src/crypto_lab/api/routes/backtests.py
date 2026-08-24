from __future__ import annotations

from uuid import UUID, uuid5

from fastapi import APIRouter, HTTPException, Query, Request, status

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.backtest_evaluation import (
    BacktestResultDto,
    BacktestRunDto,
    CreateBacktestRunRequest,
    EquityPageDto,
    TradePageDto,
    equity_to_dto,
    result_to_dto,
    run_to_dto,
    trade_to_dto,
)
from crypto_lab.domain.backtest.configuration import BacktestConfiguration
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode

router = APIRouter(prefix="/api/v1", tags=["backtests"])


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
        raise HTTPException(404, "Backtest run not found")
    return success_envelope(run_to_dto(run), "Backtest run loaded.", request_id(request))


@router.get("/backtest-results/{result_id}", response_model=SuccessEnvelope[BacktestResultDto])
async def get_backtest_result(
    request: Request, result_id: UUID
) -> SuccessEnvelope[BacktestResultDto]:
    result = await request.app.state.container.get_backtest.get(result_id)
    if result is None:
        raise HTTPException(404, "Backtest result not found")
    return success_envelope(result_to_dto(result), "Backtest result loaded.", request_id(request))


@router.get("/backtest-results/{result_id}/trades", response_model=SuccessEnvelope[TradePageDto])
async def list_backtest_trades(
    request: Request,
    result_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, alias="pageSize", ge=1, le=200),
) -> SuccessEnvelope[TradePageDto]:
    if await request.app.state.container.get_backtest.get(result_id) is None:
        raise HTTPException(404, "Backtest result not found")
    items, next_cursor = await request.app.state.container.get_backtest.trades(
        result_id, str((page - 1) * page_size), page_size
    )
    return success_envelope(
        TradePageDto(items=tuple(trade_to_dto(item) for item in items), next_cursor=next_cursor),
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
    if await request.app.state.container.get_backtest.get(result_id) is None:
        raise HTTPException(404, "Backtest result not found")
    items, next_cursor = await request.app.state.container.get_backtest.equity(
        result_id, str((page - 1) * page_size), page_size
    )
    return success_envelope(
        EquityPageDto(items=tuple(equity_to_dto(item) for item in items), next_cursor=next_cursor),
        "Backtest equity loaded.",
        request_id(request),
    )
