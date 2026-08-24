from __future__ import annotations

from copy import deepcopy

import httpx
import pytest
from fastapi.routing import APIWebSocketRoute
from pydantic import TypeAdapter, ValidationError

from crypto_lab.api.schemas.market_data import (
    CandleUpdatedEvent,
    MarketDataCommandEnvelope,
    MarketDataEventEnvelope,
    SubscribeMarketDataCommand,
)
from crypto_lab.main import create_app
from tests.contract.test_market_data_api import build_test_container

SELECTION = {"provider": "BINANCE", "pair": "BTCUSDT", "timeframe": "5m"}
CANDLE = {
    **SELECTION,
    "openTime": "2024-01-01T00:00:00.000Z",
    "closeTime": "2024-01-01T00:04:59.999Z",
    "open": "100",
    "high": "102",
    "low": "99",
    "close": "101.25",
    "volume": "12.5",
    "closed": False,
    "receivedAt": "2026-08-13T12:00:00.000Z",
}


@pytest.fixture
async def api() -> httpx.AsyncClient:
    container, _ = build_test_container()
    app = create_app(container)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_rest_history_retains_accepted_versioned_candle_shape(
    api: httpx.AsyncClient,
) -> None:
    response = await api.get(
        "/api/v1/market-data/candles",
        params={
            **SELECTION,
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:10:00.000Z",
            "limit": 2,
            "schemaVersion": "1",
        },
        headers={"X-Request-ID": "req-history"},
    )

    assert response.status_code == 200
    envelope = response.json()
    assert set(envelope) == {"success", "message", "data", "timestamp", "requestId"}
    assert envelope["success"] is True
    assert envelope["requestId"] == "req-history"
    assert set(envelope["data"]) == {
        "schemaVersion",
        "selection",
        "range",
        "completeness",
        "missingRanges",
        "candles",
    }
    assert envelope["data"]["schemaVersion"] == "1"
    assert envelope["data"]["selection"] == SELECTION
    assert [item["openTime"] for item in envelope["data"]["candles"]] == [
        "2024-01-01T00:00:00.000Z",
        "2024-01-01T00:05:00.000Z",
    ]
    assert isinstance(envelope["data"]["candles"][0]["open"], str)


@pytest.mark.asyncio
async def test_rest_unsupported_version_retains_stable_error_shape(api: httpx.AsyncClient) -> None:
    response = await api.get(
        "/api/v1/market-data/candles",
        params={
            **SELECTION,
            "startTime": "2024-01-01T00:00:00.000Z",
            "endTime": "2024-01-01T00:10:00.000Z",
            "limit": 2,
            "schemaVersion": "2",
        },
        headers={"X-Request-ID": "req-version"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert set(payload) == {"success", "message", "error", "timestamp", "requestId"}
    assert payload["success"] is False
    assert payload["requestId"] == "req-version"
    assert payload["error"] == {
        "code": "MARKET_VERSION_UNSUPPORTED",
        "retryable": False,
        "details": None,
    }


def test_websocket_command_and_candle_event_match_the_accepted_v1_shape() -> None:
    command_adapter = TypeAdapter(MarketDataCommandEnvelope)
    event_adapter = TypeAdapter(MarketDataEventEnvelope)
    command = {
        "eventType": "SUBSCRIBE_MARKET_DATA",
        "version": "1",
        "requestId": "req-01",
        "occurredAt": "2026-08-13T10:00:00Z",
        "payload": {"slotId": "slot-1", "selection": SELECTION},
    }
    event = {
        "eventType": "CANDLE_UPDATED",
        "version": "1",
        "eventId": "evt-201",
        "occurredAt": "2026-08-13T10:00:01Z",
        "payload": {"selection": SELECTION, "revision": 7, "candle": CANDLE},
    }

    parsed_command = command_adapter.validate_python(command)
    parsed_event = event_adapter.validate_python(event)

    assert isinstance(parsed_command, SubscribeMarketDataCommand)
    assert isinstance(parsed_event, CandleUpdatedEvent)
    assert command_adapter.dump_python(parsed_command, by_alias=True, mode="json") == command
    assert (
        event_adapter.dump_python(
            parsed_event,
            by_alias=True,
            exclude_none=True,
            mode="json",
        )
        == event
    )

    unsupported = deepcopy(command)
    unsupported["version"] = "2"
    with pytest.raises(ValidationError):
        command_adapter.validate_python(unsupported)


def test_websocket_error_code_is_uppercase_and_sanitized() -> None:
    adapter = TypeAdapter(MarketDataEventEnvelope)
    error = {
        "eventType": "MARKET_DATA_ERROR",
        "version": "1",
        "eventId": "evt-202",
        "requestId": "req-02",
        "occurredAt": "2026-08-13T10:00:02Z",
        "payload": {
            "slotId": "slot-5",
            "code": "MARKET_SUBSCRIPTION_LIMIT_REACHED",
            "message": "A dashboard can use at most four chart slots.",
            "retryable": False,
        },
    }

    assert adapter.validate_python(error).payload.code == "MARKET_SUBSCRIPTION_LIMIT_REACHED"
    invalid = deepcopy(error)
    assert isinstance(invalid["payload"], dict)
    invalid["payload"]["code"] = "market_subscription_limit_reached"
    with pytest.raises(ValidationError):
        adapter.validate_python(invalid)


def test_market_data_websocket_uses_the_accepted_public_path() -> None:
    container, _ = build_test_container()
    app = create_app(container)

    websocket_paths = {route.path for route in app.routes if isinstance(route, APIWebSocketRoute)}
    assert "/ws/v1/market-data" in websocket_paths
