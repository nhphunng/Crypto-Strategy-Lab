from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum


class Timeframe(StrEnum):
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"

    @property
    def seconds(self) -> int:
        return {
            Timeframe.ONE_MINUTE: 60,
            Timeframe.FIVE_MINUTES: 300,
            Timeframe.FIFTEEN_MINUTES: 900,
            Timeframe.THIRTY_MINUTES: 1_800,
            Timeframe.ONE_HOUR: 3_600,
            Timeframe.TWO_HOURS: 7_200,
            Timeframe.FOUR_HOURS: 14_400,
            Timeframe.ONE_DAY: 86_400,
        }[self]

    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.seconds)

    def floor(self, value: datetime) -> datetime:
        value = require_utc(value)
        epoch_seconds = int(value.timestamp())
        floored = epoch_seconds - (epoch_seconds % self.seconds)
        return datetime.fromtimestamp(floored, tz=UTC)

    def is_aligned(self, value: datetime) -> bool:
        value = require_utc(value)
        return value == self.floor(value)

    def close_time(self, open_time: datetime) -> datetime:
        open_time = require_utc(open_time)
        if not self.is_aligned(open_time):
            raise ValueError("open_time must be aligned to timeframe")
        return open_time + self.duration - timedelta(milliseconds=1)


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be an aware UTC instant")
    return value.astimezone(UTC)
