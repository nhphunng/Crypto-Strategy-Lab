from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from tests.fixtures.market_data import make_candle

from crypto_lab.application.market_data.candle_merge import (
    CandleUpdate,
    ClosedCandleConflictError,
    merge_live_candle,
)
from crypto_lab.domain.market_data.candle import Candle

START = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
RECEIVED_AT = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def candle(
    interval: int = 0,
    *,
    close: str = "101.25",
    closed: bool = False,
    received_offset: int = 0,
) -> Candle:
    return make_candle(
        START + timedelta(minutes=5 * interval),
        close=close,
        closed=closed,
        received_at=RECEIVED_AT + timedelta(seconds=received_offset),
    )


def test_candle_identity_and_ohlcv_are_validated_before_merge() -> None:
    item = candle()

    assert item.identity == ("BINANCE", "BTCUSDT", "5m", START)
    with pytest.raises(ValueError, match="high"):
        replace(item, high=Decimal("100"))


def test_open_update_replaces_same_identity_and_increments_revision() -> None:
    initial = candle(close="100.50")
    changed = candle(close="101.00", received_offset=1)

    first = merge_live_candle((), initial, limit=1_000)
    updated = merge_live_candle(first, changed, limit=1_000)
    duplicate = merge_live_candle(updated, changed, limit=1_000)

    assert first == (CandleUpdate(candle=initial, revision=1),)
    assert updated == (CandleUpdate(candle=changed, revision=2),)
    assert duplicate == updated


def test_closed_candle_is_terminal_and_conflicting_closed_update_is_rejected() -> None:
    opened = candle(close="100.50")
    closed = candle(close="101.00", closed=True, received_offset=1)
    regression = candle(close="101.25", closed=False, received_offset=2)
    conflicting_closed = candle(close="101.25", closed=True, received_offset=3)

    series = merge_live_candle((), opened, limit=1_000)
    closed_series = merge_live_candle(series, closed, limit=1_000)

    assert closed_series == (CandleUpdate(candle=closed, revision=2),)
    assert merge_live_candle(closed_series, closed, limit=1_000) == closed_series
    assert merge_live_candle(closed_series, regression, limit=1_000) == closed_series
    with pytest.raises(ClosedCandleConflictError):
        merge_live_candle(closed_series, conflicting_closed, limit=1_000)


def test_out_of_order_live_identity_is_ignored_and_buffer_remains_bounded() -> None:
    series: tuple[CandleUpdate, ...] = ()
    for item in (candle(0, closed=True), candle(1), candle(2)):
        series = merge_live_candle(series, item, limit=2)

    assert [update.candle.open_time for update in series] == [
        START + timedelta(minutes=5),
        START + timedelta(minutes=10),
    ]
    assert merge_live_candle(series, candle(0, closed=True), limit=2) == series

    advanced = merge_live_candle(series, candle(3), limit=2)
    assert [update.candle.open_time for update in advanced] == [
        START + timedelta(minutes=10),
        START + timedelta(minutes=15),
    ]


def test_merge_requires_a_positive_bound() -> None:
    with pytest.raises(ValueError, match="limit"):
        merge_live_candle((), candle(), limit=0)
