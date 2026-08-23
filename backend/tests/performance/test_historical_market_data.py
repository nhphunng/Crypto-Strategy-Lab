from __future__ import annotations

from datetime import UTC, datetime, timedelta
from time import perf_counter

import pytest

from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from tests.fixtures.market_data import FakeProvider, FixedClock, make_candle

pytestmark = [pytest.mark.performance, pytest.mark.integration]


@pytest.mark.asyncio
async def test_local_500_candle_read_p95_under_300_ms(
    postgres_repository: SqlAlchemyMarketDataRepository,
) -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_MINUTE)
    requested = TimeRange(start, start + timedelta(minutes=500))
    candles = tuple(
        make_candle(
            start + timedelta(minutes=index),
            selection=selection,
        )
        for index in range(500)
    )
    await postgres_repository.store_closed_candles(candles)
    samples: list[float] = []
    for _ in range(20):
        began = perf_counter()
        assert len(await postgres_repository.read_candles(selection, requested)) == 500
        samples.append((perf_counter() - began) * 1000)
    samples.sort()
    p95 = samples[int(len(samples) * 0.95) - 1]
    assert p95 < 300, {"p95_ms": p95, "samples": len(samples)}


@pytest.mark.asyncio
async def test_deterministic_10000_candle_acquisition_under_60_seconds(
    postgres_repository: SqlAlchemyMarketDataRepository,
) -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_MINUTE)
    requested = TimeRange(start, start + timedelta(minutes=10_000))
    candles = tuple(
        make_candle(start + timedelta(minutes=index), selection=selection)
        for index in range(10_000)
    )
    service = HistoricalMarketDataService(
        postgres_repository,
        FakeProvider(candles),
        FixedClock(datetime(2026, 8, 13, tzinfo=UTC)),
    )
    began = perf_counter()
    result = await service.get_range(selection, requested, limit=10_000)
    duration = perf_counter() - began
    assert len(result.candles) == 10_000
    assert duration < 60, {"duration_seconds": duration, "count": len(result.candles)}
