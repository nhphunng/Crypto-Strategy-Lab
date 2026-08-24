from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from crypto_lab.api.common import ErrorDetail, ErrorEnvelope
from crypto_lab.api.middleware import request_id
from crypto_lab.application.leaderboard.errors import LeaderboardError
from crypto_lab.application.market_data.errors import ErrorDescriptor, MarketDataError
from crypto_lab.domain.market_data.candle import format_utc_millis

logger = logging.getLogger(__name__)

_STATUS_BY_CODE = {
    "MARKET_REQUEST_MALFORMED": 400,
    "MARKET_VERSION_UNSUPPORTED": 400,
    "MARKET_PROVIDER_UNSUPPORTED": 422,
    "MARKET_PAIR_UNSUPPORTED": 422,
    "MARKET_TIMEFRAME_UNSUPPORTED": 422,
    "MARKET_RANGE_INVALID": 422,
    "MARKET_RANGE_UNALIGNED": 422,
    "MARKET_RANGE_NOT_CLOSED": 422,
    "MARKET_RANGE_TOO_LARGE": 422,
    "MARKET_PROVIDER_PAYLOAD_INVALID": 502,
    "PROVIDER_RATE_LIMITED": 429,
    "MARKET_PROVIDER_UNAVAILABLE": 503,
    "MARKET_CANDLE_CONFLICT": 409,
    "MARKET_DATASET_BUILDING": 202,
    "MARKET_DATASET_INCOMPLETE": 409,
    "MARKET_DATASET_NOT_FOUND": 404,
    "MARKET_DATASET_INTEGRITY_FAILED": 500,
    "MARKET_INTERNAL_ERROR": 500,
    "LEADERBOARD_NOT_FOUND": 404,
    "LEADERBOARD_ENTRY_NOT_FOUND": 404,
    "LEADERBOARD_QUERY_INVALID": 422,
    "LEADERBOARD_RANGE_INVALID": 422,
    "LEADERBOARD_DEPENDENCY_UNAVAILABLE": 503,
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(MarketDataError)
    async def market_error(request: Request, error: MarketDataError) -> JSONResponse:
        return _response(request, error.descriptor)

    @app.exception_handler(LeaderboardError)
    async def leaderboard_error(request: Request, error: LeaderboardError) -> JSONResponse:
        return _response(request, error.descriptor)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        fields = sorted(
            {
                str(item["loc"][-1])
                for item in error.errors()
                if item.get("loc") and item["loc"][-1] != "body"
            }
        )
        return _response(
            request,
            ErrorDescriptor(
                "MARKET_REQUEST_MALFORMED",
                "The request is malformed.",
                details={"fields": fields},
            ),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_request_error",
            extra={"fields": {"request_id": request_id(request)}},
        )
        return _response(
            request,
            ErrorDescriptor("MARKET_INTERNAL_ERROR", "An unexpected error occurred."),
        )


def _response(request: Request, descriptor: ErrorDescriptor) -> JSONResponse:
    envelope = ErrorEnvelope(
        message=descriptor.message,
        error=ErrorDetail(
            code=descriptor.code,
            retryable=descriptor.retryable,
            details=dict(descriptor.details) if descriptor.details else None,
        ),
        timestamp=format_utc_millis(datetime.now(UTC)),
        request_id=request_id(request),
    )
    headers = {}
    if descriptor.retry_after_seconds is not None:
        headers["Retry-After"] = str(descriptor.retry_after_seconds)
    return JSONResponse(
        status_code=_STATUS_BY_CODE.get(descriptor.code, 500),
        content=envelope.model_dump(by_alias=True),
        headers=headers,
    )
