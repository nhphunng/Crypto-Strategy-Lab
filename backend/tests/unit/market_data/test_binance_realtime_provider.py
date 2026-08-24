from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

import pytest
from tests.fixtures.market_data import FixedClock

from crypto_lab.application.market_data.ports import (
    RealtimeProviderEvent,
    RealtimeProviderEventType,
)
from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.infrastructure.market_data.binance_realtime_provider import (
    BinanceRealtimeMarketProvider,
    BinanceRealtimePayloadError,
    RealtimeSocket,
    map_binance_kline,
)

SELECTION = MarketSelection("BINANCE", "BTCUSDT", "5m")
OPEN_TIME = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
RECEIVED_AT = datetime(2026, 8, 13, 10, 0, 1, tzinfo=UTC)


def _payload(**kline_overrides: object) -> dict[str, object]:
    kline: dict[str, object] = {
        "t": int(OPEN_TIME.timestamp() * 1000),
        "T": int(SELECTION.timeframe.close_time(OPEN_TIME).timestamp() * 1000),
        "s": "BTCUSDT",
        "i": "5m",
        "o": "67234.12",
        "h": "67250.00",
        "l": "67220.50",
        "c": "67241.30",
        "v": "12.50",
        "x": False,
    }
    kline.update(kline_overrides)
    return {"e": "kline", "E": int(RECEIVED_AT.timestamp() * 1000), "k": kline}


class _FakeSocket:
    def __init__(self, messages: list[dict[str, object]]) -> None:
        self._messages = [json.dumps(message) for message in messages]
        self.closed: tuple[int, str] | None = None

    async def recv(self) -> str | bytes:
        if not self._messages:
            await asyncio.sleep(3600)
        return self._messages.pop(0)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = (code, reason)


class _FakeConnection:
    def __init__(self, socket: RealtimeSocket) -> None:
        self._socket = socket
        self.entered = False

    async def __aenter__(self) -> RealtimeSocket:
        self.entered = True
        return self._socket

    async def __aexit__(self, *exc_info: object) -> None:
        del exc_info


def _provider(socket: _FakeSocket) -> BinanceRealtimeMarketProvider:
    return BinanceRealtimeMarketProvider(
        FixedClock(RECEIVED_AT),
        websocket_url="wss://stream.binance.com:9443/ws",
        heartbeat_interval_seconds=0.005,
        stale_after_seconds=0.01,
        connection_factory=lambda _url, _heartbeat, _stale: _FakeConnection(socket),
    )


def test_maps_binance_kline_to_provider_neutral_candle() -> None:
    candle = map_binance_kline(_payload(), SELECTION, received_at=RECEIVED_AT)

    assert candle.selection == SELECTION
    assert candle.open_time == OPEN_TIME
    assert candle.close_time == SELECTION.timeframe.close_time(OPEN_TIME)
    assert str(candle.close) == "67241.30"
    assert candle.closed is False
    assert candle.received_at == RECEIVED_AT


@pytest.mark.parametrize(
    "override",
    [
        {"s": "ETHUSDT"},
        {"i": "1h"},
        {"o": 67234.12},
        {"h": "not-a-decimal"},
        {"T": int(OPEN_TIME.timestamp() * 1000)},
    ],
)
def test_rejects_mismatched_or_malformed_provider_payload(
    override: dict[str, object],
) -> None:
    with pytest.raises(BinanceRealtimePayloadError):
        map_binance_kline(_payload(**override), SELECTION, received_at=RECEIVED_AT)


@pytest.mark.asyncio
async def test_heartbeat_timeout_yields_disconnected_with_reason() -> None:
    provider = _provider(_FakeSocket(messages=[]))

    async for event in provider.stream(SELECTION):
        assert event.event_type is RealtimeProviderEventType.DISCONNECTED
        assert event.reason_code == "PROVIDER_HEARTBEAT_TIMEOUT"
        break


@pytest.mark.asyncio
async def test_reconnect_uses_a_fresh_connection_generation() -> None:
    socket = _FakeSocket(messages=[])
    provider = _provider(socket)
    first = provider.stream(SELECTION)
    event = await anext(first)
    assert event.event_type is RealtimeProviderEventType.DISCONNECTED
    await first.aclose()

    socket.closed = None
    second = provider.stream(SELECTION)
    event = await anext(second)
    assert event.event_type is RealtimeProviderEventType.DISCONNECTED
    await second.aclose()
    assert provider.last_closed_checkpoint(SELECTION) is None


@pytest.mark.asyncio
async def test_last_closed_checkpoint_tracks_only_closed_candles() -> None:
    provider = _provider(
        _FakeSocket(
            messages=[
                _payload(),
                _payload(x=True, c="67250.00"),
            ]
        )
    )

    events: list[RealtimeProviderEvent] = []
    async for event in provider.stream(SELECTION):
        events.append(event)
        if len(events) == 2:
            break
    assert [event.event_type for event in events] == [
        RealtimeProviderEventType.CANDLE,
        RealtimeProviderEventType.CANDLE,
    ]
    assert provider.last_closed_checkpoint(SELECTION) == OPEN_TIME


@pytest.mark.asyncio
async def test_last_closed_checkpoint_reports_none_before_any_closed_candle() -> None:
    provider = _provider(_FakeSocket(messages=[_payload()]))

    async for event in provider.stream(SELECTION):
        assert event.event_type is RealtimeProviderEventType.CANDLE
        break
    assert provider.last_closed_checkpoint(SELECTION) is None


@pytest.mark.asyncio
async def test_release_closes_the_active_socket_and_clears_checkpoint() -> None:
    socket = _FakeSocket(messages=[_payload(x=True, c="67250.00")])
    provider = _provider(socket)
    stream = provider.stream(SELECTION)
    event = await anext(stream)
    assert event.event_type is RealtimeProviderEventType.CANDLE
    assert provider.last_closed_checkpoint(SELECTION) == OPEN_TIME

    await provider.release(SELECTION)
    assert socket.closed is not None
    assert socket.closed[0] == 1000
    assert provider.last_closed_checkpoint(SELECTION) is None
    await stream.aclose()
