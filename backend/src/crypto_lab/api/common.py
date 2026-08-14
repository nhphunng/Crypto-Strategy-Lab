from __future__ import annotations

from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from crypto_lab.domain.market_data.candle import format_utc_millis

T = TypeVar("T")


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SuccessEnvelope(ApiModel, Generic[T]):
    success: bool = True
    message: str
    data: T
    timestamp: str
    request_id: str = Field(alias="requestId")


class ErrorDetail(ApiModel):
    code: str
    retryable: bool
    details: dict[str, object] | None = None


class ErrorEnvelope(ApiModel):
    success: bool = False
    message: str
    error: ErrorDetail
    timestamp: str
    request_id: str = Field(alias="requestId")


def success_envelope(data: T, message: str, request_id: str) -> SuccessEnvelope[T]:
    return SuccessEnvelope(
        message=message,
        data=data,
        timestamp=format_utc_millis(datetime.now(UTC)),
        requestId=request_id,
    )
