from datetime import UTC, datetime, timedelta

import pytest
from tests.fixtures.market_data import (
    FakeProvider,
    FixedClock,
    InMemoryMarketDataRepository,
    make_candle,
)

from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
RANGE = TimeRange(
    datetime(2026, 8, 13, 10, tzinfo=UTC),
    datetime(2026, 8, 13, 10, 10, tzinfo=UTC),
)


@pytest.mark.asyncio
async def test_materialization_is_idempotent_and_provider_free_after_completion() -> None:
    rows = (make_candle(RANGE.start_time), make_candle(RANGE.start_time + timedelta(minutes=5)))
    repository = InMemoryMarketDataRepository()
    provider = FakeProvider(rows)
    historical = HistoricalMarketDataService(repository, provider, FixedClock(NOW))
    service = DatasetService(
        repository,
        historical,
        FixedClock(NOW),
        lease_duration=timedelta(seconds=60),
        max_dataset_candles=100,
    )

    first = await service.materialize(SELECTION, RANGE)
    second = await service.materialize(SELECTION, RANGE)
    page = await service.list_candles(first.dataset.id, None, 1)

    assert first.created and first.dataset.status is DatasetStatus.COMPLETE
    assert not second.created and second.dataset.id == first.dataset.id
    assert second.dataset.checksum == first.dataset.checksum
    assert len(provider.calls) == 1
    assert page.has_more and len(page.candles) == 1


@pytest.mark.asyncio
async def test_incomplete_acquisition_never_finalizes_complete_dataset() -> None:
    repository = InMemoryMarketDataRepository()
    historical = HistoricalMarketDataService(repository, FakeProvider(()), FixedClock(NOW))
    service = DatasetService(
        repository,
        historical,
        FixedClock(NOW),
        lease_duration=timedelta(seconds=60),
        max_dataset_candles=100,
    )

    result = await service.materialize(SELECTION, RANGE)

    assert result.dataset.status is DatasetStatus.INCOMPLETE
    assert result.dataset.checksum is None
