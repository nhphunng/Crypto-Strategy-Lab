from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from importlib import import_module
from typing import Protocol, cast

import pytest
from pydantic import TypeAdapter
from starlette.websockets import WebSocketDisconnect

from crypto_lab.api.schemas.market_data import MarketDataEventEnvelope
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.domain.market_data.timeframe import Timeframe
from tests.fixtures.market_data import FixedClock, make_candle
from tests.integration.fakes.fake_realtime_market_provider import (
    FakeRealtimeMarketProvider,
)

NOW = datetime(2026, 8, 13, 10, tzinfo=UTC)
FIVE_MINUTES = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
ONE_HOUR = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_HOUR)
EVENT_ADAPTER: TypeAdapter[MarketDataEventEnvelope] = TypeAdapter(MarketDataEventEnvelope)
_DISCONNECT = object()


class _Channel(Protocol):
    async def run(self, websocket: _FakeWebSocket) -> None: ...


class _ChannelFactory(Protocol):
    def __call__(
        self,
        *,
        provider: FakeRealtimeMarketProvider,
        clock: FixedClock,
        event_id_factory: Callable[[], str],
    ) -> _Channel: ...


class _EventIds:
    def __init__(self) -> None:
        self._next = 1

    def __call__(self) -> str:
        value = f"evt-{self._next:03d}"
        self._next += 1
        return value


class _FakeWebSocket:
    """Application-level WebSocket double with deterministic inbound/outbound queues."""

    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict[str, object]] = []
        self._accepted = asyncio.Event()
        self._incoming: asyncio.Queue[dict[str, object] | object] = asyncio.Queue()
        self._sent_changed = asyncio.Condition()

    async def accept(
        self,
        subprotocol: str | None = None,
        headers: Iterable[tuple[bytes, bytes]] | None = None,
    ) -> None:
        del subprotocol, headers
        self.accepted = True
        self._accepted.set()

    async def receive_json(self, mode: str = "text") -> dict[str, object]:
        del mode
        message = await self._incoming.get()
        if message is _DISCONNECT:
            raise WebSocketDisconnect(code=1000)
        if not isinstance(message, dict):
            raise AssertionError("fake WebSocket received a non-object command")
        return message

    async def send_json(self, data: object, mode: str = "text") -> None:
        del mode
        if not isinstance(data, dict) or not all(isinstance(key, str) for key in data):
            raise AssertionError("market-data channel must send a JSON object")
        message = cast(dict[str, object], data)
        async with self._sent_changed:
            self.sent.append(message)
            self._sent_changed.notify_all()

    async def feed_json(self, message: dict[str, object]) -> None:
        await self._incoming.put(message)

    async def disconnect(self) -> None:
        await self._incoming.put(_DISCONNECT)

    async def wait_until_accepted(self) -> None:
        await asyncio.wait_for(self._accepted.wait(), timeout=1)

    async def wait_for_message(
        self,
        predicate: Callable[[dict[str, object]], bool],
        *,
        occurrence: int = 1,
    ) -> dict[str, object]:
        if occurrence < 1:
            raise ValueError("occurrence must be positive")

        def matches() -> list[dict[str, object]]:
            return [message for message in self.sent if predicate(message)]

        async with self._sent_changed:
            await asyncio.wait_for(
                self._sent_changed.wait_for(lambda: len(matches()) >= occurrence),
                timeout=1,
            )
            return matches()[occurrence - 1]


@pytest.fixture
def channel_factory() -> _ChannelFactory:
    module_name = "crypto_lab.api.websocket.market_data_channel"
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            "RED T016: T022 must provide crypto_lab.api.websocket.market_data_channel",
            pytrace=False,
        )

    channel_type = getattr(module, "MarketDataChannel", None)
    if channel_type is None:
        pytest.fail("RED T016: T022 must provide MarketDataChannel", pytrace=False)
    return cast(_ChannelFactory, channel_type)


def _selection_payload(selection: MarketSelection) -> dict[str, object]:
    return {
        "provider": selection.provider.value,
        "pair": selection.pair,
        "timeframe": selection.timeframe.value,
    }


def _subscribe(
    slot_id: str,
    selection: MarketSelection,
    request_id: str,
) -> dict[str, object]:
    return {
        "eventType": "SUBSCRIBE_MARKET_DATA",
        "version": "1",
        "requestId": request_id,
        "occurredAt": format_utc_millis(NOW),
        "payload": {"slotId": slot_id, "generation": 1, "selection": _selection_payload(selection)},
    }


def _payload(message: dict[str, object]) -> dict[str, object]:
    payload = message.get("payload")
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


def _is_event(event_type: str) -> Callable[[dict[str, object]], bool]:
    return lambda message: message.get("eventType") == event_type


def _is_state(
    *,
    state: str | None = None,
    request_id: str | None = None,
) -> Callable[[dict[str, object]], bool]:
    def predicate(message: dict[str, object]) -> bool:
        if message.get("eventType") != "SUBSCRIPTION_STATE_CHANGED":
            return False
        payload = message.get("payload")
        if not isinstance(payload, dict):
            return False
        return (state is None or payload.get("state") == state) and (
            request_id is None or message.get("requestId") == request_id
        )

    return predicate


async def _start_channel(
    channel_factory: _ChannelFactory,
    provider: FakeRealtimeMarketProvider,
) -> tuple[_FakeWebSocket, asyncio.Task[None]]:
    channel = channel_factory(
        provider=provider,
        clock=FixedClock(NOW),
        event_id_factory=_EventIds(),
    )
    websocket = _FakeWebSocket()
    task = asyncio.create_task(channel.run(websocket))
    await websocket.wait_until_accepted()
    return websocket, task


async def _stop_channel(websocket: _FakeWebSocket, task: asyncio.Task[None]) -> None:
    if not task.done():
        await websocket.disconnect()
    try:
        await asyncio.wait_for(task, timeout=1)
    finally:
        if not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


@pytest.mark.asyncio
async def test_open_closed_and_duplicate_updates_reach_websocket_once(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task = await _start_channel(channel_factory, provider)

    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-subscribe"))
        await provider.wait_until_streaming(FIVE_MINUTES)

        loading = await websocket.wait_for_message(
            _is_state(state="LOADING", request_id="req-subscribe")
        )
        EVENT_ADAPTER.validate_python(loading)
        assert loading["version"] == "1"
        assert loading["occurredAt"] == format_utc_millis(NOW)
        assert _payload(loading)["slotIds"] == ["slot-1"]

        open_candle = make_candle(
            NOW,
            selection=FIVE_MINUTES,
            close="101",
            closed=False,
            received_at=NOW + timedelta(seconds=1),
        )
        closed_candle = make_candle(
            NOW,
            selection=FIVE_MINUTES,
            close="101.25",
            closed=True,
            received_at=NOW + timedelta(seconds=2),
        )
        next_candle = make_candle(
            NOW + timedelta(minutes=5),
            selection=FIVE_MINUTES,
            close="101.50",
            closed=False,
            received_at=NOW + timedelta(minutes=5, seconds=1),
        )

        provider.publish(open_candle, occurred_at=NOW + timedelta(seconds=1))
        await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=1)
        await websocket.wait_for_message(_is_state(state="LIVE"))
        provider.publish(closed_candle, occurred_at=NOW + timedelta(seconds=2))
        provider.publish(closed_candle, occurred_at=NOW + timedelta(seconds=3))
        provider.publish(next_candle, occurred_at=NOW + timedelta(minutes=5, seconds=1))

        await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=3)
        updates = [
            message for message in websocket.sent if message.get("eventType") == "CANDLE_UPDATED"
        ]
        assert len(updates) == 3, "the exact duplicate closed Candle must be suppressed"
        for update in updates:
            EVENT_ADAPTER.validate_python(update)
            assert update.get("requestId") is None

        first_payload, closed_payload, next_payload = map(_payload, updates)
        assert [
            cast(dict[str, object], payload["candle"])["closed"]
            for payload in (first_payload, closed_payload, next_payload)
        ] == [False, True, False]
        assert [
            cast(dict[str, object], payload["candle"])["openTime"]
            for payload in (first_payload, closed_payload, next_payload)
        ] == [
            format_utc_millis(NOW),
            format_utc_millis(NOW),
            format_utc_millis(NOW + timedelta(minutes=5)),
        ]
        assert closed_payload["revision"] == cast(int, first_payload["revision"]) + 1
        assert len({message["eventId"] for message in websocket.sent}) == len(websocket.sent)
    finally:
        await _stop_channel(websocket, channel_task)

    assert provider.release_calls == [FIVE_MINUTES]


@pytest.mark.asyncio
async def test_equal_selections_share_one_stream_and_other_selection_stays_isolated(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task = await _start_channel(channel_factory, provider)

    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-slot-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        await websocket.feed_json(_subscribe("slot-2", FIVE_MINUTES, "req-slot-2"))
        shared_ack = await websocket.wait_for_message(_is_state(request_id="req-slot-2"))
        EVENT_ADAPTER.validate_python(shared_ack)
        assert _payload(shared_ack)["slotIds"] == ["slot-1", "slot-2"]
        assert provider.stream_calls.count(FIVE_MINUTES) == 1

        await websocket.feed_json(_subscribe("slot-3", ONE_HOUR, "req-slot-3"))
        await provider.wait_until_streaming(ONE_HOUR)
        assert provider.stream_calls.count(ONE_HOUR) == 1

        five_minute_candle = make_candle(
            NOW,
            selection=FIVE_MINUTES,
            closed=False,
            received_at=NOW + timedelta(seconds=1),
        )
        one_hour_candle = make_candle(
            NOW,
            selection=ONE_HOUR,
            closed=False,
            received_at=NOW + timedelta(seconds=2),
        )
        provider.publish(five_minute_candle, occurred_at=NOW + timedelta(seconds=1))
        provider.publish(one_hour_candle, occurred_at=NOW + timedelta(seconds=2))
        await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=2)

        updates = [
            message for message in websocket.sent if message.get("eventType") == "CANDLE_UPDATED"
        ]
        delivered_timeframes = [
            cast(dict[str, object], _payload(message)["selection"])["timeframe"]
            for message in updates
        ]
        assert delivered_timeframes.count("5m") == 1
        assert delivered_timeframes.count("1h") == 1
        assert provider.release_calls == []
    finally:
        await _stop_channel(websocket, channel_task)

    assert provider.release_calls.count(FIVE_MINUTES) == 1
    assert provider.release_calls.count(ONE_HOUR) == 1
