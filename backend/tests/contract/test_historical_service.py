from datetime import UTC, datetime, timedelta

import pytest

from crypto_lab.application.market_data.errors import MarketDataError, ProviderPayloadInvalid
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import Completeness, TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from tests.fixtures.market_data import (
    FakeProvider,
    FixedClock,
    InMemoryMarketDataRepository,
    make_candle,
)

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
RANGE = TimeRange(
    datetime(2026, 8, 13, 10, tzinfo=UTC),
    datetime(2026, 8, 13, 10, 20, tzinfo=UTC),
)


@pytest.mark.asyncio
async def test_fetches_missing_range_then_reuses_local_coverage() -> None:
    rows = tuple(make_candle(RANGE.start_time + index * timedelta(minutes=5)) for index in range(4))
    repository = InMemoryMarketDataRepository()
    provider = FakeProvider(rows)
    service = HistoricalMarketDataService(repository, provider, FixedClock(NOW))

    first = await service.get_range(SELECTION, RANGE, limit=4)
    second = await service.get_range(SELECTION, RANGE, limit=4)

    assert first.completeness is Completeness.COMPLETE
    assert first.candles == tuple(sorted(rows, key=lambda item: item.open_time))
    assert second.candles == first.candles
    assert provider.calls == [RANGE]


@pytest.mark.asyncio
async def test_fetches_only_exact_gap_and_preserves_covered_neighbors() -> None:
    rows = tuple(make_candle(RANGE.start_time + index * timedelta(minutes=5)) for index in range(4))
    repository = InMemoryMarketDataRepository()
    await repository.store_closed_candles((rows[0], rows[3]))
    provider = FakeProvider(rows)
    service = HistoricalMarketDataService(repository, provider, FixedClock(NOW))

    result = await service.get_range(SELECTION, RANGE, limit=4)

    assert result.completeness is Completeness.COMPLETE
    assert provider.calls == [TimeRange(rows[1].open_time, rows[3].open_time)]


@pytest.mark.asyncio
async def test_partial_and_empty_results_report_exact_missing_ranges() -> None:
    repository = InMemoryMarketDataRepository()
    existing = make_candle(RANGE.start_time)
    await repository.store_closed_candles((existing,))
    service = HistoricalMarketDataService(repository, FakeProvider(()), FixedClock(NOW))

    partial = await service.get_range(SELECTION, RANGE, limit=4)
    empty_service = HistoricalMarketDataService(
        InMemoryMarketDataRepository(), FakeProvider(()), FixedClock(NOW)
    )
    empty = await empty_service.get_range(SELECTION, RANGE, limit=4)

    assert partial.completeness is Completeness.PARTIAL
    assert partial.missing_ranges == (
        TimeRange(RANGE.start_time + timedelta(minutes=5), RANGE.end_time),
    )
    assert empty.completeness is Completeness.EMPTY
    assert empty.missing_ranges == (RANGE,)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("requested", "limit", "code"),
    [
        (
            TimeRange(RANGE.start_time + timedelta(minutes=1), RANGE.end_time),
            10,
            "MARKET_RANGE_UNALIGNED",
        ),
        (RANGE, 3, "MARKET_RANGE_TOO_LARGE"),
        (
            TimeRange(NOW, NOW + timedelta(minutes=5)),
            10,
            "MARKET_RANGE_NOT_CLOSED",
        ),
    ],
)
async def test_invalid_ranges_fail_before_provider_access(
    requested: TimeRange, limit: int, code: str
) -> None:
    provider = FakeProvider(())
    service = HistoricalMarketDataService(InMemoryMarketDataRepository(), provider, FixedClock(NOW))

    with pytest.raises(MarketDataError) as caught:
        await service.get_range(SELECTION, requested, limit=limit)

    assert caught.value.descriptor.code == code
    assert provider.calls == []


def test_rejects_provider_pages_that_violate_the_application_port_contract() -> None:
    wrong_selection = MarketSelection("BINANCE", "ETHUSDT", Timeframe.FIVE_MINUTES)
    invalid_page = (make_candle(RANGE.start_time, selection=wrong_selection),)

    with pytest.raises(ProviderPayloadInvalid) as caught:
        HistoricalMarketDataService._validate_page(SELECTION, RANGE, invalid_page)

    assert caught.value.descriptor.code == "MARKET_PROVIDER_PAYLOAD_INVALID"
