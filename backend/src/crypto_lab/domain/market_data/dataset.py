from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.market_data.candle import Candle, MarketSelection, format_utc_millis
from crypto_lab.domain.market_data.ranges import TimeRange, derive_historical_range


class DatasetStatus(StrEnum):
    BUILDING = "BUILDING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CandleDataset:
    id: UUID
    schema_version: str
    selection: MarketSelection
    time_range: TimeRange
    status: DatasetStatus
    candle_count: int | None
    checksum: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if self.schema_version != "1":
            raise ValueError("unsupported dataset schema version")
        if self.status is DatasetStatus.COMPLETE:
            if self.candle_count is None or self.candle_count <= 0:
                raise ValueError("complete dataset requires a positive candle_count")
            if self.checksum is None or len(self.checksum) != 64:
                raise ValueError("complete dataset requires SHA-256 checksum")
            if self.completed_at is None:
                raise ValueError("complete dataset requires completed_at")

    @property
    def consumer_eligible(self) -> bool:
        return self.status is DatasetStatus.COMPLETE


def dataset_request_key(
    selection: MarketSelection,
    time_range: TimeRange,
    schema_version: str = "1",
) -> str:
    payload = "|".join(
        (
            schema_version,
            selection.provider,
            selection.pair,
            selection.timeframe.value,
            format_utc_millis(time_range.start_time),
            format_utc_millis(time_range.end_time),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def calculate_dataset_checksum(candles: tuple[Candle, ...]) -> str:
    payload = "".join(f"{candle.canonical_line()}\n" for candle in candles)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_complete_dataset_membership(
    selection: MarketSelection,
    time_range: TimeRange,
    candles: tuple[Candle, ...],
) -> str:
    result = derive_historical_range(selection, time_range, candles)
    if result.missing_ranges:
        raise ValueError("dataset membership must provide complete coverage")
    return calculate_dataset_checksum(result.candles)
