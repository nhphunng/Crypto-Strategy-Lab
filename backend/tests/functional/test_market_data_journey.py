"""Functional regression test for the historical market-data user journey.

Walks the same sequence a client performs end to end: discover dimensions,
preview a historical range, materialize it as a dataset, request it again to
confirm idempotent reuse, then page through every Candle the dataset holds.
Runs against an in-memory repository and a fake provider so the journey stays
fast and network-free while still exercising the real ASGI app and routes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from crypto_lab.api.dependencies import Container
from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app
from tests.fixtures.market_data import (
    FakeProvider,
    FixedClock,
    InMemoryMarketDataRepository,
    make_candle,
)

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
START = datetime(2024, 1, 1, tzinfo=UTC)
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
CANDLE_COUNT = 5
FULL_RANGE = TimeRange(START, START + timedelta(minutes=5 * CANDLE_COUNT))


def build_test_container(pair: str = "BTCUSDT") -> tuple[Container, FakeProvider]:
    clock = FixedClock(NOW)
    repository = InMemoryMarketDataRepository()
    settings = Settings(_env_file=None)
    selection = MarketSelection("BINANCE", pair, Timeframe.FIVE_MINUTES)
    candles = tuple(
        make_candle(START + timedelta(minutes=5 * i), selection=selection)
        for i in range(CANDLE_COUNT)
    )
    provider = FakeProvider(candles)
    historical = HistoricalMarketDataService(
        repository,
        provider,
        clock,
        supported_pairs=frozenset(settings.capabilities.pairs),
        supported_timeframes=frozenset(settings.capabilities.timeframes),
    )
    datasets = DatasetService(
        repository,
        historical,
        clock,
        lease_duration=timedelta(seconds=60),
        max_dataset_candles=100,
    )
    return (
        Container(
            settings=settings,
            clock=clock,
            repository=repository,
            historical=historical,
            datasets=datasets,
        ),
        provider,
    )


@pytest.fixture
async def api() -> httpx.AsyncClient:
    container, _ = build_test_container()
    app = create_app(container)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
@pytest.mark.parametrize("pair", ("ETHUSDT", "SOLUSDT"))
async def test_supported_altcoin_pair_fetches_matching_fake_provider_candles(pair: str) -> None:
    container, provider = build_test_container(pair)
    app = create_app(container)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/market-data/candles",
            params={
                "provider": "BINANCE",
                "pair": pair,
                "timeframe": "5m",
                "startTime": "2024-01-01T00:00:00.000Z",
                "endTime": "2024-01-01T00:25:00.000Z",
                "limit": CANDLE_COUNT,
                "schemaVersion": "1",
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["completeness"] == "COMPLETE"
    assert data["selection"]["pair"] == pair
    assert len(data["candles"]) == CANDLE_COUNT
    assert {candle["pair"] for candle in data["candles"]} == {pair}
    assert provider.calls == [FULL_RANGE]


async def test_discover_preview_materialize_and_page_a_dataset(api: httpx.AsyncClient) -> None:
    dimensions = await api.get("/api/v1/market-data/dimensions")
    assert dimensions.status_code == 200
    assert "BINANCE" in dimensions.json()["data"]["providers"]

    preview = await api.get(
        "/api/v1/market-data/candles",
        params={
            "provider": "BINANCE",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:25:00.000Z",
            "schemaVersion": "1",
        },
    )
    assert preview.status_code == 200
    assert len(preview.json()["data"]["candles"]) == CANDLE_COUNT

    body = {
        "schemaVersion": "1",
        "selection": {"provider": "BINANCE", "pair": "BTCUSDT", "timeframe": "5m"},
        "range": {
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:25:00.000Z",
        },
    }
    created = await api.post("/api/v1/market-data/datasets", json=body)
    assert created.status_code == 201
    dataset = created.json()["data"]
    dataset_id = dataset["datasetId"]
    assert dataset["candleCount"] == CANDLE_COUNT
    checksum = dataset["checksum"]

    reused = await api.post("/api/v1/market-data/datasets", json=body)
    assert reused.status_code == 200
    assert reused.json()["data"]["datasetId"] == dataset_id
    assert reused.json()["data"]["checksum"] == checksum

    fetched = await api.get(f"/api/v1/market-data/datasets/{dataset_id}")
    assert fetched.status_code == 200
    assert fetched.json()["data"]["checksum"] == checksum

    collected: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        response = await api.get(
            f"/api/v1/market-data/datasets/{dataset_id}/candles",
            params={"pageSize": 2, **({"cursor": cursor} if cursor else {})},
        )
        assert response.status_code == 200
        page = response.json()["data"]
        collected.extend(candle["openTime"] for candle in page["candles"])
        pages += 1
        if not page["hasMore"]:
            assert page["nextCursor"] is None
            break
        cursor = page["nextCursor"]
        assert cursor

    assert pages == 3
    assert len(collected) == CANDLE_COUNT
    assert collected == sorted(collected)
    assert len(set(collected)) == CANDLE_COUNT


async def test_a_dataset_never_shrinks_the_requested_range_below_full_coverage(
    api: httpx.AsyncClient,
) -> None:
    body = {
        "schemaVersion": "1",
        "selection": {"provider": "BINANCE", "pair": "BTCUSDT", "timeframe": "5m"},
        "range": {
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T01:00:00.000Z",
        },
    }

    created = await api.post("/api/v1/market-data/datasets", json=body)

    assert created.status_code == 409
    assert created.json()["error"]["code"] == "MARKET_DATASET_INCOMPLETE"
