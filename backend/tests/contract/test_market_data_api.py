from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from tests.fixtures.market_data import (
    FakeProvider,
    FixedClock,
    InMemoryMarketDataRepository,
    make_candle,
)

from crypto_lab.api.dependencies import Container
from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app

NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
START = datetime(2024, 1, 1, tzinfo=UTC)
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
RANGE = TimeRange(START, START + timedelta(minutes=10))


def build_test_container() -> tuple[Container, FakeProvider]:
    clock = FixedClock(NOW)
    repository = InMemoryMarketDataRepository()
    provider = FakeProvider((make_candle(START), make_candle(START + timedelta(minutes=5))))
    historical = HistoricalMarketDataService(repository, provider, clock)
    datasets = DatasetService(
        repository,
        historical,
        clock,
        lease_duration=timedelta(seconds=60),
        max_dataset_candles=100,
    )
    return (
        Container(
            settings=Settings(_env_file=None),
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
async def test_dimensions_and_historical_range_use_versioned_camel_case_envelopes(
    api: httpx.AsyncClient,
) -> None:
    dimensions = await api.get("/api/v1/market-data/dimensions", headers={"X-Request-ID": "req-1"})
    history = await api.get(
        "/api/v1/market-data/candles",
        params={
            "provider": "BINANCE",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:10:00.000Z",
            "limit": 2,
            "schemaVersion": "1",
        },
    )

    assert dimensions.status_code == 200
    assert dimensions.json()["requestId"] == "req-1"
    assert dimensions.json()["data"]["maxRangeLimit"] == 1000
    payload = history.json()
    assert history.status_code == 200 and payload["success"] is True
    assert payload["data"]["schemaVersion"] == "1"
    assert payload["data"]["range"]["startTime"].endswith(".000Z")
    assert payload["data"]["candles"][0]["open"] == "100"
    assert "open_time" not in payload["data"]["candles"][0]


@pytest.mark.asyncio
async def test_invalid_selection_range_and_version_use_stable_error_envelope(
    api: httpx.AsyncClient,
) -> None:
    response = await api.get(
        "/api/v1/market-data/candles",
        params={
            "provider": "BINANCE",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "startTime": "2024-01-01T00:01:00.000Z",
            "endTime": "2024-01-01T00:10:00.000Z",
            "limit": 2,
            "schemaVersion": "1",
        },
    )
    wrong_version = await api.get(
        "/api/v1/market-data/candles",
        params={
            "provider": "BINANCE",
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:10:00.000Z",
            "schemaVersion": "2",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MARKET_RANGE_UNALIGNED"
    assert wrong_version.status_code == 400
    assert wrong_version.json()["error"]["code"] == "MARKET_VERSION_UNSUPPORTED"


@pytest.mark.asyncio
async def test_materialize_reuse_and_page_dataset(api: httpx.AsyncClient) -> None:
    body = {
        "schemaVersion": "1",
        "selection": {"provider": "BINANCE", "pair": "BTCUSDT", "timeframe": "5m"},
        "range": {
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:10:00.000Z",
        },
    }
    created = await api.post("/api/v1/market-data/datasets", json=body)
    reused = await api.post("/api/v1/market-data/datasets", json=body)
    dataset_id = created.json()["data"]["datasetId"]
    page = await api.get(
        f"/api/v1/market-data/datasets/{dataset_id}/candles", params={"pageSize": 1}
    )

    assert created.status_code == 201 and reused.status_code == 200
    assert reused.json()["data"]["datasetId"] == dataset_id
    assert page.status_code == 200
    assert page.json()["data"]["hasMore"] is True
    assert page.json()["data"]["nextCursor"]
