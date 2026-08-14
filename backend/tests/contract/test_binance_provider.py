from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from tests.fixtures.market_data import FixedClock

from crypto_lab.application.market_data.errors import ProviderPayloadInvalid
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.binance.market_data_provider import BinanceMarketDataProvider

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
RANGE = TimeRange(
    datetime(2024, 1, 1, tzinfo=UTC),
    datetime(2024, 1, 1, 0, 10, tzinfo=UTC),
)


def row(open_time: datetime, close: str = "101.23000000") -> list[object]:
    open_ms = int(open_time.timestamp() * 1000)
    close_ms = int((open_time + timedelta(minutes=5)).timestamp() * 1000) - 1
    return [
        open_ms,
        "100.10000000",
        "102.00000000",
        "99.50000000",
        close,
        "12.50000000",
        close_ms,
        "unused",
    ]


async def collect(provider: BinanceMarketDataProvider) -> tuple[object, ...]:
    items: list[object] = []
    async for page in provider.iter_historical(SELECTION, RANGE):
        items.extend(page)
    return tuple(items)


@pytest.mark.asyncio
async def test_maps_exact_decimals_and_exclusive_provider_end() -> None:
    observed: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(
            200, json=[row(RANGE.start_time), row(RANGE.start_time + timedelta(minutes=5))]
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect(BinanceMarketDataProvider(client, FixedClock(NOW)))

    assert len(result) == 2
    first = result[0]
    assert first.open == Decimal("100.10000000")  # type: ignore[union-attr]
    assert first.content_hash  # type: ignore[union-attr]
    assert observed[0].url.params["endTime"] == str(int(RANGE.end_time.timestamp() * 1000) - 1)


@pytest.mark.asyncio
async def test_overlapping_repeated_page_terminates_without_duplicates() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[row(RANGE.start_time)])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await collect(BinanceMarketDataProvider(client, FixedClock(NOW)))

    assert len(result) == 1
    assert calls == 2


@pytest.mark.asyncio
async def test_rate_limit_honors_retry_after_then_succeeds() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "2"})
        return httpx.Response(200, json=[])

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = BinanceMarketDataProvider(client, FixedClock(NOW), sleep=sleep)
        assert await collect(provider) == ()

    assert calls == 2
    assert delays == [2]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__(1, 100.1),
        lambda value: value.__setitem__(1, "1e2"),
        lambda value: value.__setitem__(6, value[6] + 1),
        lambda value: value.__setitem__(0, True),
    ],
)
async def test_rejects_malformed_provider_rows(
    mutate: Callable[[list[object]], object],
) -> None:
    payload = row(RANGE.start_time)
    mutate(payload)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[payload])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderPayloadInvalid):
            await collect(BinanceMarketDataProvider(client, FixedClock(NOW)))
