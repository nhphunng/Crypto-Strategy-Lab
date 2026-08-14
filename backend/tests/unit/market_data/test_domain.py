from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from crypto_lab.domain.market_data.candle import Candle, MarketSelection, canonical_decimal
from crypto_lab.domain.market_data.ranges import Completeness, TimeRange, derive_historical_range
from crypto_lab.domain.market_data.timeframe import Timeframe

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def candle(open_time: datetime, *, close: str = "101.25") -> Candle:
    return Candle(
        provider="BINANCE",
        pair="BTCUSDT",
        timeframe=Timeframe.FIVE_MINUTES,
        open_time=open_time,
        close_time=Timeframe.FIVE_MINUTES.close_time(open_time),
        open=Decimal("100.00"),
        high=Decimal("102.00"),
        low=Decimal("99.50"),
        close=Decimal(close),
        volume=Decimal("12.5000"),
        closed=True,
        received_at=NOW,
    )


@pytest.mark.parametrize("value", list(Timeframe))
def test_timeframe_alignment_and_close_time(value: Timeframe) -> None:
    aligned = value.floor(NOW)
    assert value.is_aligned(aligned)
    assert value.close_time(aligned) == aligned + value.duration - timedelta(milliseconds=1)
    assert not value.is_aligned(aligned + timedelta(milliseconds=1))


def test_candle_identity_and_canonical_content_are_stable() -> None:
    item = candle(datetime(2026, 8, 13, 10, 0, tzinfo=UTC))
    assert item.identity == ("BINANCE", "BTCUSDT", "5m", item.open_time)
    assert canonical_decimal(item.volume) == "12.5"
    assert "|100|102|99.5|101.25|12.5|true" in item.canonical_line()
    assert len(item.content_hash) == 64


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"high": Decimal("100")}, "high"),
        ({"low": Decimal("101.26")}, "low"),
        ({"open": Decimal("0")}, "positive"),
        ({"volume": Decimal("-1")}, "non-negative"),
        ({"open": float(100)}, "float"),
        ({"close_time": NOW}, "close_time"),
    ],
)
def test_candle_rejects_invalid_values(overrides: dict[str, object], message: str) -> None:
    values: dict[str, object] = {
        "provider": "BINANCE",
        "pair": "BTCUSDT",
        "timeframe": Timeframe.FIVE_MINUTES,
        "open_time": datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
        "close_time": datetime(2026, 8, 13, 10, 4, 59, 999000, tzinfo=UTC),
        "open": Decimal("100"),
        "high": Decimal("102"),
        "low": Decimal("99"),
        "close": Decimal("101.25"),
        "volume": Decimal("1"),
        "closed": True,
        "received_at": NOW,
    }
    values.update(overrides)
    with pytest.raises((TypeError, ValueError), match=message):
        Candle(**values)  # type: ignore[arg-type]


def test_half_open_range_derives_exact_missing_ranges() -> None:
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
    requested = TimeRange(
        datetime(2026, 8, 13, 10, 0, tzinfo=UTC),
        datetime(2026, 8, 13, 10, 20, tzinfo=UTC),
    )
    items = (candle(requested.start_time), candle(requested.start_time + timedelta(minutes=15)))

    result = derive_historical_range(selection, requested, items)

    assert result.completeness is Completeness.PARTIAL
    assert result.missing_ranges == (
        TimeRange(
            datetime(2026, 8, 13, 10, 5, tzinfo=UTC),
            datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
        ),
    )


def test_range_rejects_naive_or_reversed_time() -> None:
    with pytest.raises(ValueError, match="UTC"):
        TimeRange(datetime(2026, 1, 1), datetime(2026, 1, 2))
    with pytest.raises(ValueError, match="later"):
        TimeRange(NOW, NOW)
