from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from crypto_lab.domain.market_data.selection import MarketSelection as MarketSelection
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc

type CandleIdentity = tuple[str, str, str, datetime]
type DecimalInput = Decimal | str | int


def exact_decimal(value: DecimalInput, *, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TypeError(f"{field} must not be a bool or float")
    result = value if isinstance(value, Decimal) else Decimal(value)
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("decimal must be finite")
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def format_utc_millis(value: datetime) -> str:
    value = require_utc(value)
    milliseconds = value.microsecond // 1000
    return f"{value:%Y-%m-%dT%H:%M:%S}.{milliseconds:03d}Z"


@dataclass(frozen=True, slots=True)
class Candle:
    provider: str
    pair: str
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    closed: bool
    received_at: datetime

    def __post_init__(self) -> None:
        MarketSelection(self.provider, self.pair, self.timeframe)
        open_time = require_utc(self.open_time)
        close_time = require_utc(self.close_time)
        received_at = require_utc(self.received_at)
        if not self.timeframe.is_aligned(open_time):
            raise ValueError("open_time must be aligned to timeframe")
        if close_time != self.timeframe.close_time(open_time):
            raise ValueError("close_time must be the final millisecond of the interval")
        prices = {
            "open": exact_decimal(self.open, field="open"),
            "high": exact_decimal(self.high, field="high"),
            "low": exact_decimal(self.low, field="low"),
            "close": exact_decimal(self.close, field="close"),
        }
        volume = exact_decimal(self.volume, field="volume")
        if any(value <= 0 for value in prices.values()):
            raise ValueError("OHLC prices must be positive")
        if volume < 0:
            raise ValueError("volume must be non-negative")
        if prices["high"] < max(prices.values()):
            raise ValueError("high must be at least every OHLC price")
        if prices["low"] > min(prices.values()):
            raise ValueError("low must be at most every OHLC price")
        object.__setattr__(self, "open_time", open_time)
        object.__setattr__(self, "close_time", close_time)
        object.__setattr__(self, "received_at", received_at)
        for name, value in prices.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "volume", volume)

    @property
    def selection(self) -> MarketSelection:
        return MarketSelection(self.provider, self.pair, self.timeframe)

    @property
    def identity(self) -> CandleIdentity:
        return self.provider, self.pair, self.timeframe.value, self.open_time

    def canonical_line(self) -> str:
        fields = (
            "1",
            self.provider,
            self.pair,
            self.timeframe.value,
            format_utc_millis(self.open_time),
            format_utc_millis(self.close_time),
            canonical_decimal(self.open),
            canonical_decimal(self.high),
            canonical_decimal(self.low),
            canonical_decimal(self.close),
            canonical_decimal(self.volume),
            "true" if self.closed else "false",
        )
        return "|".join(fields)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_line().encode("utf-8")).hexdigest()
