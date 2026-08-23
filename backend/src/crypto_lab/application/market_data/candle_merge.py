from __future__ import annotations

from dataclasses import dataclass

from crypto_lab.domain.market_data.candle import Candle


class ClosedCandleConflictError(ValueError):
    """A closed Candle is immutable once accepted into the live series."""

    def __init__(self, accepted: Candle, conflicting: Candle) -> None:
        self.accepted = accepted
        self.conflicting = conflicting
        super().__init__("conflicting update for a terminal closed Candle")


@dataclass(frozen=True, slots=True)
class CandleUpdate:
    candle: Candle
    revision: int

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("revision must be positive")


def merge_live_candle(
    series: tuple[CandleUpdate, ...],
    incoming: Candle,
    *,
    limit: int,
) -> tuple[CandleUpdate, ...]:
    """Merge one ordered realtime update into a deterministic bounded tail."""

    if limit < 1 or limit > 1_000:
        raise ValueError("limit must be between one and 1,000 Candles")
    _validate_series(series)
    if not series:
        return (CandleUpdate(incoming, 1),)

    tail = series[-1]
    if incoming.selection != tail.candle.selection:
        raise ValueError("incoming Candle selection must match the live series")
    if incoming.open_time < tail.candle.open_time:
        return series
    if incoming.open_time > tail.candle.open_time:
        return (*series, CandleUpdate(incoming, 1))[-limit:]

    accepted = tail.candle
    if accepted.closed:
        if not incoming.closed:
            return series
        if incoming.content_hash == accepted.content_hash:
            return series
        raise ClosedCandleConflictError(accepted, incoming)
    if incoming.content_hash == accepted.content_hash:
        return series
    return (*series[:-1], CandleUpdate(incoming, tail.revision + 1))


def _validate_series(series: tuple[CandleUpdate, ...]) -> None:
    if not series:
        return
    selection = series[0].candle.selection
    previous_open_time = series[0].candle.open_time
    for index, update in enumerate(series):
        if update.candle.selection != selection:
            raise ValueError("live series must contain one MarketSelection")
        if index > 0 and update.candle.open_time <= previous_open_time:
            raise ValueError("live series must be unique and chronological")
        previous_open_time = update.candle.open_time
