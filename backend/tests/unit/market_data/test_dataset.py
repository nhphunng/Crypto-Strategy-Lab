from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.dataset import (
    CandleDataset,
    DatasetStatus,
    calculate_dataset_checksum,
    dataset_request_key,
)
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe


def test_dataset_request_key_and_checksum_are_deterministic() -> None:
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_MINUTE)
    requested = TimeRange(
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 1, 0, 2, tzinfo=UTC),
    )
    candles = tuple(
        Candle(
            provider=selection.provider,
            pair=selection.pair,
            timeframe=selection.timeframe,
            open_time=requested.start_time + timedelta(minutes=index),
            close_time=requested.start_time
            + timedelta(minutes=index + 1)
            - timedelta(milliseconds=1),
            open=Decimal("1"),
            high=Decimal("2"),
            low=Decimal("0.5"),
            close=Decimal("1.5"),
            volume=Decimal("3"),
            closed=True,
            received_at=datetime(2026, 8, 13, tzinfo=UTC),
        )
        for index in range(2)
    )

    assert dataset_request_key(selection, requested) == dataset_request_key(selection, requested)
    assert len(calculate_dataset_checksum(candles)) == 64


def test_complete_dataset_is_terminal_and_requires_integrity_fields() -> None:
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_HOUR)
    requested = TimeRange(
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 1, 1, tzinfo=UTC),
    )
    dataset = CandleDataset(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        schema_version="1",
        selection=selection,
        time_range=requested,
        status=DatasetStatus.COMPLETE,
        candle_count=1,
        checksum="a" * 64,
        failure_code=None,
        created_at=datetime(2026, 8, 13, tzinfo=UTC),
        updated_at=datetime(2026, 8, 13, tzinfo=UTC),
        completed_at=datetime(2026, 8, 13, tzinfo=UTC),
    )
    assert dataset.consumer_eligible
