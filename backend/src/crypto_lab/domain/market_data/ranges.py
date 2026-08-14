from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc


@dataclass(frozen=True, slots=True, order=True)
class TimeRange:
    start_time: datetime
    end_time: datetime

    def __post_init__(self) -> None:
        start = require_utc(self.start_time)
        end = require_utc(self.end_time)
        if end <= start:
            raise ValueError("end_time must be later than start_time")
        object.__setattr__(self, "start_time", start)
        object.__setattr__(self, "end_time", end)

    def validate_alignment(self, timeframe: Timeframe) -> None:
        if not timeframe.is_aligned(self.start_time) or not timeframe.is_aligned(self.end_time):
            raise ValueError("range boundaries must be aligned to timeframe")

    def expected_count(self, timeframe: Timeframe) -> int:
        self.validate_alignment(timeframe)
        seconds = int((self.end_time - self.start_time).total_seconds())
        return seconds // timeframe.seconds

    def contains_open(self, value: datetime) -> bool:
        value = require_utc(value)
        return self.start_time <= value < self.end_time

    def expected_opens(self, timeframe: Timeframe) -> tuple[datetime, ...]:
        count = self.expected_count(timeframe)
        return tuple(self.start_time + index * timeframe.duration for index in range(count))


class Completeness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"


@dataclass(frozen=True, slots=True)
class HistoricalCandleRange:
    selection: MarketSelection
    time_range: TimeRange
    completeness: Completeness
    missing_ranges: tuple[TimeRange, ...]
    candles: tuple[Candle, ...]
    schema_version: str = "1"


def coalesce_missing_ranges(
    time_range: TimeRange,
    timeframe: Timeframe,
    present_opens: Iterable[datetime],
) -> tuple[TimeRange, ...]:
    present = set(present_opens)
    missing = [value for value in time_range.expected_opens(timeframe) if value not in present]
    if not missing:
        return ()
    ranges: list[TimeRange] = []
    range_start = previous = missing[0]
    for current in missing[1:]:
        if current != previous + timeframe.duration:
            ranges.append(TimeRange(range_start, previous + timeframe.duration))
            range_start = current
        previous = current
    ranges.append(TimeRange(range_start, previous + timeframe.duration))
    return tuple(ranges)


def derive_historical_range(
    selection: MarketSelection,
    time_range: TimeRange,
    candles: Iterable[Candle],
) -> HistoricalCandleRange:
    time_range.validate_alignment(selection.timeframe)
    by_open: dict[datetime, Candle] = {}
    for candle in candles:
        if candle.selection != selection:
            raise ValueError("Candle selection does not match range selection")
        if not candle.closed:
            raise ValueError("historical ranges contain only closed Candles")
        if not time_range.contains_open(candle.open_time):
            raise ValueError("Candle is outside requested range")
        existing = by_open.get(candle.open_time)
        if existing is not None and existing.content_hash != candle.content_hash:
            raise ValueError("conflicting Candle identity in range")
        by_open[candle.open_time] = candle
    ordered = tuple(by_open[key] for key in sorted(by_open))
    missing = coalesce_missing_ranges(time_range, selection.timeframe, by_open)
    if not missing:
        completeness = Completeness.COMPLETE
    elif not ordered:
        completeness = Completeness.EMPTY
    else:
        completeness = Completeness.PARTIAL
    return HistoricalCandleRange(selection, time_range, completeness, missing, ordered)
