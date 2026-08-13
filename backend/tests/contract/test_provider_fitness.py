from datetime import UTC, datetime, timedelta

import httpx
import pytest
from tests.fixtures.market_data import FakeProvider, FixedClock, make_candle

from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.binance.market_data_provider import BinanceMarketDataProvider


@pytest.mark.asyncio
async def test_fake_and_provider_adapter_emit_the_same_canonical_contract() -> None:
    now = datetime(2026, 8, 13, 12, tzinfo=UTC)
    open_time = datetime(2024, 1, 1, tzinfo=UTC)
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
    requested = TimeRange(open_time, open_time + timedelta(minutes=5))
    expected = make_candle(open_time, received_at=now)
    raw = [
        int(open_time.timestamp() * 1000),
        "100",
        "102",
        "99",
        "101.25",
        "12.5",
        int((open_time + timedelta(minutes=5)).timestamp() * 1000) - 1,
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[raw])

    fake = FakeProvider((expected,))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = BinanceMarketDataProvider(client, FixedClock(now))
        fake_pages = [page async for page in fake.iter_historical(selection, requested)]
        adapter_pages = [page async for page in adapter.iter_historical(selection, requested)]

    assert adapter_pages[0][0].canonical_line() == fake_pages[0][0].canonical_line()
