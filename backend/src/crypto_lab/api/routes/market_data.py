from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request
from fastapi.responses import JSONResponse

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.market_data import (
    CandleDatasetDto,
    CandleRangeDto,
    DatasetCandlePageDto,
    MarketDimensionsDto,
    MaterializeDatasetRequest,
    dataset_to_dto,
    historical_range_to_dto,
    page_to_dto,
)
from crypto_lab.application.market_data.errors import invalid_request
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe

router = APIRouter(prefix="/api/v1/market-data", tags=["market-data"])


@router.get(
    "/dimensions",
    response_model=SuccessEnvelope[MarketDimensionsDto],
)
async def dimensions(request: Request) -> SuccessEnvelope[MarketDimensionsDto]:
    container = request.app.state.container
    settings = container.settings
    capabilities = settings.capabilities
    data = MarketDimensionsDto(
        schema_version="1",
        providers=capabilities.providers,
        pairs=capabilities.pairs,
        timeframes=capabilities.timeframes,
        default_range_limit=settings.default_range_candles,
        max_range_limit=settings.max_range_candles,
        max_dataset_candles=settings.max_dataset_candles,
    )
    return success_envelope(data, "Market dimensions loaded.", request_id(request))


@router.get("/candles", response_model=SuccessEnvelope[CandleRangeDto])
async def historical_candles(
    request: Request,
    provider: str,
    pair: str,
    timeframe: str,
    start_time: datetime = Query(alias="startTime"),
    end_time: datetime = Query(alias="endTime"),
    limit: int = 500,
    schema_version: str = Query(default="1", alias="schemaVersion"),
) -> SuccessEnvelope[CandleRangeDto]:
    _validate_version(schema_version)
    container = request.app.state.container
    if limit < 1 or limit > container.settings.max_range_candles:
        raise invalid_request(
            "MARKET_RANGE_TOO_LARGE", "limit must be within the documented range."
        )
    selection, time_range = _domain_request(provider, pair, timeframe, start_time, end_time)
    result = await container.historical.get_range(
        selection, time_range, limit=limit, request_id=request_id(request)
    )
    return success_envelope(
        historical_range_to_dto(result),
        "Historical Candles loaded.",
        request_id(request),
    )


@router.post("/datasets", response_model=SuccessEnvelope[CandleDatasetDto])
async def materialize_dataset(
    request: Request,
    body: MaterializeDatasetRequest,
) -> JSONResponse:
    _validate_version(body.schema_version)
    selection, time_range = _domain_request(
        body.selection.provider,
        body.selection.pair,
        body.selection.timeframe,
        body.range.start_time,
        body.range.end_time,
    )
    result = await request.app.state.container.datasets.materialize(
        selection, time_range, request_id=request_id(request)
    )
    if result.dataset.status is DatasetStatus.INCOMPLETE:
        raise invalid_request(
            "MARKET_DATASET_INCOMPLETE",
            "The provider could not supply complete closed-Candle coverage.",
        )
    status_code = 202 if result.building else 201 if result.created else 200
    envelope = success_envelope(
        dataset_to_dto(result.dataset),
        "Dataset build is in progress."
        if result.building
        else "Dataset materialized."
        if result.created
        else "Existing dataset reused.",
        request_id(request),
    )
    headers = {"Retry-After": "1"} if result.building else None
    return JSONResponse(
        status_code=status_code,
        content=envelope.model_dump(by_alias=True),
        headers=headers,
    )


@router.get("/datasets/{datasetId}", response_model=SuccessEnvelope[CandleDatasetDto])
async def get_dataset(
    request: Request, dataset_id: UUID = Path(alias="datasetId")
) -> SuccessEnvelope[CandleDatasetDto]:
    dataset = await request.app.state.container.datasets.get(dataset_id)
    return success_envelope(dataset_to_dto(dataset), "Dataset loaded.", request_id(request))


@router.get(
    "/datasets/{datasetId}/candles",
    response_model=SuccessEnvelope[DatasetCandlePageDto],
)
async def list_dataset_candles(
    request: Request,
    dataset_id: UUID = Path(alias="datasetId"),
    cursor: str | None = Query(default=None, max_length=128),
    page_size: int = Query(default=500, alias="pageSize"),
) -> SuccessEnvelope[DatasetCandlePageDto]:
    try:
        page = await request.app.state.container.datasets.list_candles(
            dataset_id, cursor, page_size
        )
    except ValueError as error:
        raise invalid_request("MARKET_REQUEST_MALFORMED", "The cursor is invalid.") from error
    return success_envelope(
        page_to_dto(str(dataset_id), page), "Dataset Candles loaded.", request_id(request)
    )


def _validate_version(value: str) -> None:
    if value != "1":
        raise invalid_request(
            "MARKET_VERSION_UNSUPPORTED", "Only market-data contract version 1 is supported."
        )


def _domain_request(
    provider: str,
    pair: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
) -> tuple[MarketSelection, TimeRange]:
    if provider != provider.upper():
        raise invalid_request(
            "MARKET_PROVIDER_UNSUPPORTED", "The requested provider is not supported."
        )
    if pair != pair.upper():
        raise invalid_request("MARKET_PAIR_UNSUPPORTED", "The requested pair is not supported.")
    try:
        parsed_timeframe = Timeframe(timeframe)
    except ValueError as error:
        raise invalid_request(
            "MARKET_TIMEFRAME_UNSUPPORTED", "The requested timeframe is not supported."
        ) from error
    try:
        return MarketSelection(provider, pair, parsed_timeframe), TimeRange(start_time, end_time)
    except ValueError as error:
        raise invalid_request(
            "MARKET_RANGE_INVALID", "The requested time range is invalid."
        ) from error
