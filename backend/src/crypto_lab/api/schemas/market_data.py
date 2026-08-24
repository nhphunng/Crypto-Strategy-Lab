from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, field_validator

from crypto_lab.api.common import ApiModel
from crypto_lab.application.market_data.ports import CandlePage
from crypto_lab.domain.market_data.candle import (
    Candle,
    MarketSelection,
    canonical_decimal,
    format_utc_millis,
)
from crypto_lab.domain.market_data.dataset import CandleDataset
from crypto_lab.domain.market_data.ranges import HistoricalCandleRange, TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe


class MarketSelectionDto(ApiModel):
    provider: str
    pair: str
    timeframe: Timeframe


class TimeRangeDto(ApiModel):
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")


class CandleDto(ApiModel):
    provider: str
    pair: str
    timeframe: Timeframe
    open_time: str = Field(alias="openTime")
    close_time: str = Field(alias="closeTime")
    open: str
    high: str
    low: str
    close: str
    volume: str
    closed: bool
    received_at: str = Field(alias="receivedAt")


class CandleRangeDto(ApiModel):
    schema_version: Literal["1"] = Field(alias="schemaVersion")
    selection: MarketSelectionDto
    range: TimeRangeDto
    completeness: str
    missing_ranges: tuple[TimeRangeDto, ...] = Field(alias="missingRanges")
    candles: tuple[CandleDto, ...]


class MarketSelectionRequest(ApiModel):
    provider: str
    pair: str
    timeframe: str


class TimeRangeRequest(ApiModel):
    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")


class MaterializeDatasetRequest(ApiModel):
    schema_version: str = Field(alias="schemaVersion")
    selection: MarketSelectionRequest
    range: TimeRangeRequest


class CandleDatasetDto(ApiModel):
    schema_version: Literal["1"] = Field(alias="schemaVersion")
    dataset_id: str = Field(alias="datasetId")
    selection: MarketSelectionDto
    range: TimeRangeDto
    status: str
    candle_count: int | None = Field(alias="candleCount")
    checksum: str | None
    failure_code: str | None = Field(alias="failureCode")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    completed_at: str | None = Field(alias="completedAt")


class DatasetCandlePageDto(ApiModel):
    schema_version: Literal["1"] = Field(alias="schemaVersion")
    dataset_id: str = Field(alias="datasetId")
    candles: tuple[CandleDto, ...]
    next_cursor: str | None = Field(alias="nextCursor")
    has_more: bool = Field(alias="hasMore")


class MarketDimensionsDto(ApiModel):
    schema_version: Literal["1"] = Field(alias="schemaVersion")
    providers: tuple[str, ...]
    pairs: tuple[str, ...]
    timeframes: tuple[Timeframe, ...]
    default_range_limit: int = Field(alias="defaultRangeLimit")
    max_range_limit: int = Field(alias="maxRangeLimit")
    max_dataset_candles: int = Field(alias="maxDatasetCandles")


def selection_to_dto(value: MarketSelection) -> MarketSelectionDto:
    return MarketSelectionDto(provider=value.provider, pair=value.pair, timeframe=value.timeframe)


def range_to_dto(value: TimeRange) -> TimeRangeDto:
    return TimeRangeDto(
        start_time=format_utc_millis(value.start_time),
        end_time=format_utc_millis(value.end_time),
    )


def candle_to_dto(value: Candle) -> CandleDto:
    return CandleDto(
        provider=value.provider,
        pair=value.pair,
        timeframe=value.timeframe,
        open_time=format_utc_millis(value.open_time),
        close_time=format_utc_millis(value.close_time),
        open=canonical_decimal(value.open),
        high=canonical_decimal(value.high),
        low=canonical_decimal(value.low),
        close=canonical_decimal(value.close),
        volume=canonical_decimal(value.volume),
        closed=value.closed,
        received_at=format_utc_millis(value.received_at),
    )


def historical_range_to_dto(value: HistoricalCandleRange) -> CandleRangeDto:
    return CandleRangeDto(
        schema_version="1",
        selection=selection_to_dto(value.selection),
        range=range_to_dto(value.time_range),
        completeness=value.completeness.value,
        missing_ranges=tuple(range_to_dto(item) for item in value.missing_ranges),
        candles=tuple(candle_to_dto(item) for item in value.candles),
    )


def dataset_to_dto(value: CandleDataset) -> CandleDatasetDto:
    return CandleDatasetDto(
        schema_version="1",
        dataset_id=str(value.id),
        selection=selection_to_dto(value.selection),
        range=range_to_dto(value.time_range),
        status=value.status.value,
        candle_count=value.candle_count,
        checksum=value.checksum,
        failure_code=value.failure_code,
        created_at=format_utc_millis(value.created_at),
        updated_at=format_utc_millis(value.updated_at),
        completed_at=format_utc_millis(value.completed_at) if value.completed_at else None,
    )


def page_to_dto(dataset_id: str, value: CandlePage) -> DatasetCandlePageDto:
    return DatasetCandlePageDto(
        schema_version="1",
        dataset_id=dataset_id,
        candles=tuple(candle_to_dto(item) for item in value.candles),
        next_cursor=value.next_cursor,
        has_more=value.has_more,
    )


def _require_utc_timestamp(value: datetime) -> datetime:
    offset = value.utcoffset()
    if value.tzinfo is None or offset is None or offset.total_seconds() != 0:
        raise ValueError("timestamp must use UTC")
    return value


def _parse_utc_timestamp(value: str) -> datetime:
    encoded = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(encoded)
    except ValueError as error:
        raise ValueError("timestamp must be an ISO 8601 UTC instant") from error
    return _require_utc_timestamp(parsed)


type UtcTimestamp = Annotated[datetime, AfterValidator(_require_utc_timestamp)]
type UppercaseCode = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Z][A-Z0-9_]*$"),
]
type MarketDataConnectionState = Literal["LOADING", "LIVE", "STALE", "RECONNECTING", "ERROR"]


class SubscribeMarketDataPayload(ApiModel):
    slot_id: str = Field(alias="slotId", min_length=1, max_length=128)
    selection: MarketSelectionDto


class UnsubscribeMarketDataPayload(ApiModel):
    slot_id: str = Field(alias="slotId", min_length=1, max_length=128)


class RetryMarketDataPayload(ApiModel):
    slot_id: str = Field(alias="slotId", min_length=1, max_length=128)


class SubscribeMarketDataCommand(ApiModel):
    event_type: Literal["SUBSCRIBE_MARKET_DATA"] = Field(alias="eventType")
    version: Literal["1"]
    request_id: str = Field(alias="requestId", min_length=1, max_length=128)
    occurred_at: UtcTimestamp = Field(alias="occurredAt")
    payload: SubscribeMarketDataPayload


class UnsubscribeMarketDataCommand(ApiModel):
    event_type: Literal["UNSUBSCRIBE_MARKET_DATA"] = Field(alias="eventType")
    version: Literal["1"]
    request_id: str = Field(alias="requestId", min_length=1, max_length=128)
    occurred_at: UtcTimestamp = Field(alias="occurredAt")
    payload: UnsubscribeMarketDataPayload


class RetryMarketDataCommand(ApiModel):
    event_type: Literal["RETRY_MARKET_DATA"] = Field(alias="eventType")
    version: Literal["1"]
    request_id: str = Field(alias="requestId", min_length=1, max_length=128)
    occurred_at: UtcTimestamp = Field(alias="occurredAt")
    payload: RetryMarketDataPayload


type MarketDataCommandEnvelope = Annotated[
    SubscribeMarketDataCommand | UnsubscribeMarketDataCommand | RetryMarketDataCommand,
    Field(discriminator="event_type"),
]


class SubscriptionStateChangedPayload(ApiModel):
    slot_ids: tuple[str, ...] = Field(alias="slotIds", min_length=1, max_length=4)
    selection: MarketSelectionDto
    state: MarketDataConnectionState
    attempt: int = Field(ge=0, le=8)
    retry_after_ms: int | None = Field(default=None, alias="retryAfterMs", ge=0)
    last_event_at: UtcTimestamp | None = Field(default=None, alias="lastEventAt")
    reason_code: UppercaseCode | None = Field(default=None, alias="reasonCode")


class CandleUpdatedPayload(ApiModel):
    selection: MarketSelectionDto
    revision: int = Field(ge=0)
    candle: CandleDto

    @field_validator("candle")
    @classmethod
    def validate_candle_timestamps_are_utc(cls, value: CandleDto) -> CandleDto:
        _parse_utc_timestamp(value.open_time)
        _parse_utc_timestamp(value.close_time)
        _parse_utc_timestamp(value.received_at)
        return value


class MarketDataErrorPayload(ApiModel):
    slot_id: str | None = Field(default=None, alias="slotId", min_length=1, max_length=128)
    code: UppercaseCode
    message: str = Field(min_length=1, max_length=500)
    retryable: bool


class SubscriptionStateChangedEvent(ApiModel):
    event_type: Literal["SUBSCRIPTION_STATE_CHANGED"] = Field(alias="eventType")
    version: Literal["1"]
    event_id: str = Field(alias="eventId", min_length=1, max_length=128)
    request_id: str | None = Field(default=None, alias="requestId", min_length=1, max_length=128)
    occurred_at: UtcTimestamp = Field(alias="occurredAt")
    payload: SubscriptionStateChangedPayload


class CandleUpdatedEvent(ApiModel):
    event_type: Literal["CANDLE_UPDATED"] = Field(alias="eventType")
    version: Literal["1"]
    event_id: str = Field(alias="eventId", min_length=1, max_length=128)
    request_id: str | None = Field(default=None, alias="requestId", min_length=1, max_length=128)
    occurred_at: UtcTimestamp = Field(alias="occurredAt")
    payload: CandleUpdatedPayload


class MarketDataErrorEvent(ApiModel):
    event_type: Literal["MARKET_DATA_ERROR"] = Field(alias="eventType")
    version: Literal["1"]
    event_id: str = Field(alias="eventId", min_length=1, max_length=128)
    request_id: str | None = Field(default=None, alias="requestId", min_length=1, max_length=128)
    occurred_at: UtcTimestamp = Field(alias="occurredAt")
    payload: MarketDataErrorPayload


type MarketDataEventEnvelope = Annotated[
    SubscriptionStateChangedEvent | CandleUpdatedEvent | MarketDataErrorEvent,
    Field(discriminator="event_type"),
]
