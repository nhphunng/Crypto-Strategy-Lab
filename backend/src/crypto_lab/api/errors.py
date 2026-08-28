from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from crypto_lab.api.common import ErrorDetail, ErrorEnvelope
from crypto_lab.api.middleware import request_id
from crypto_lab.application.leaderboard.errors import LeaderboardError
from crypto_lab.application.market_data.errors import ErrorDescriptor, MarketDataError
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError

logger = logging.getLogger(__name__)

_STATUS_BY_CODE = {
    "BACKTEST_CONFIGURATION_INVALID": 422,
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

_STRATEGY_STATUS = {
    ErrorCategory.INVALID_PARAMETERS: 422,
    ErrorCategory.INVALID_CONTEXT: 422,
    ErrorCategory.UNKNOWN_STRATEGY: 404,
    ErrorCategory.STRATEGY_VERSION_UNAVAILABLE: 404,
    ErrorCategory.STRATEGY_VERSION_DEPRECATED: 409,
    ErrorCategory.INCOMPATIBLE_CONTRACT_VERSION: 409,
    ErrorCategory.DUPLICATE_STRATEGY_ENTRY: 409,
    ErrorCategory.INVALID_STRATEGY_METADATA: 422,
    ErrorCategory.STRATEGY_INTENT_UNRESOLVED: 422,
    ErrorCategory.SOURCE_ACCESS_DENIED: 422,
    ErrorCategory.SOURCE_UNAVAILABLE: 422,
    ErrorCategory.GENERATION_FAILED: 502,
    ErrorCategory.STRATEGY_RULES_INCOMPLETE: 422,
    ErrorCategory.GENERATED_ARTIFACT_INVALID: 422,
    ErrorCategory.ACTIVATION_NOT_ALLOWED: 409,
}

_BACKTEST_STATUS = {
    BacktestErrorCode.CONFIGURATION_INVALID: 422,
    BacktestErrorCode.DATASET_INELIGIBLE: 422,
    BacktestErrorCode.DATASET_INTEGRITY_FAILED: 409,
    BacktestErrorCode.STRATEGY_INCOMPATIBLE: 409,
    BacktestErrorCode.SIGNAL_MISALIGNED: 422,
    BacktestErrorCode.INSUFFICIENT_CAPITAL: 422,
    BacktestErrorCode.JOB_CONFLICT: 409,
    BacktestErrorCode.EXECUTION_FAILED: 500,
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        detail = error.detail
        if isinstance(detail, dict):
            code = str(detail.get("code", f"HTTP_{error.status_code}"))
            message = str(detail.get("message", "The request could not be completed."))
            raw_details = detail.get("details")
            details = raw_details if isinstance(raw_details, dict) else None
        else:
            code = f"HTTP_{error.status_code}"
            message = str(detail)
            details = None
        return _response(
            request,
            ErrorDescriptor(code, message, details=details),
            status_code=error.status_code,
        )

    @app.exception_handler(BacktestError)
    async def backtest_error(request: Request, error: BacktestError) -> JSONResponse:
        envelope = ErrorEnvelope(
            message=error.message,
            error=ErrorDetail(
                code=error.code.value,
                retryable=False,
                details={
                    "issues": [
                        {"field": item.field, "code": item.code, "message": item.message}
                        for item in error.issues
                    ]
                }
                if error.issues
                else None,
            ),
            timestamp=format_utc_millis(datetime.now(UTC)),
            request_id=request_id(request),
        )
        return JSONResponse(
            status_code=_BACKTEST_STATUS[error.code],
            content=envelope.model_dump(by_alias=True),
        )

    @app.exception_handler(StrategyError)
    async def strategy_error(request: Request, error: StrategyError) -> JSONResponse:
        envelope = ErrorEnvelope(
            message=str(error),
            error=ErrorDetail(
                code=error.category.value,
                retryable=error.category
                in {ErrorCategory.SOURCE_UNAVAILABLE, ErrorCategory.GENERATION_FAILED},
                details={
                    "issues": [
                        {"field": item.field, "code": item.code, "message": item.message}
                        for item in error.issues
                    ]
                }
                if error.issues
                else None,
            ),
            timestamp=format_utc_millis(datetime.now(UTC)),
            request_id=request_id(request),
        )
        return JSONResponse(
            status_code=_STRATEGY_STATUS[error.category],
            content=envelope.model_dump(by_alias=True),
        )

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
        is_backtest_request = request.url.path == "/api/v1/backtest-runs"
        return _response(
            request,
            ErrorDescriptor(
                "BACKTEST_CONFIGURATION_INVALID"
                if is_backtest_request
                else "MARKET_REQUEST_MALFORMED",
                "The backtest configuration is invalid."
                if is_backtest_request
                else "The request is malformed.",
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


def _response(
    request: Request,
    descriptor: ErrorDescriptor,
    *,
    status_code: int | None = None,
) -> JSONResponse:
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
        status_code=status_code or _STATUS_BY_CODE.get(descriptor.code, 500),
        content=envelope.model_dump(by_alias=True),
        headers=headers,
    )
