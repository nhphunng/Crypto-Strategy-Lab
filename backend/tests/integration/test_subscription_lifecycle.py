from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from starlette.websockets import WebSocketDisconnect

from crypto_lab.api.websocket.market_data_channel import MarketDataChannel
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
_DISCONNECT = object()


class _EventIds:
    def __init__(self) -> None:
        self._next = 1

    def __call__(self) -> str:
        event_id = f"lifecycle-event-{self._next}"
        self._next += 1
        return event_id


class _FakeWebSocket:
    def __init__(self) -> None:
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
        if not isinstance(data, dict):
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
        def matches() -> list[dict[str, object]]:
            return [message for message in self.sent if predicate(message)]

        async with self._sent_changed:
            await asyncio.wait_for(
                self._sent_changed.wait_for(lambda: len(matches()) >= occurrence),
                timeout=1,
            )
            return matches()[occurrence - 1]


def _selection_payload(selection: MarketSelection) -> dict[str, str]:
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
        "payload": {
            "slotId": slot_id,
            "selection": _selection_payload(selection),
        },
    }


def _unsubscribe(slot_id: str, request_id: str) -> dict[str, object]:
    return {
        "eventType": "UNSUBSCRIBE_MARKET_DATA",
        "version": "1",
        "requestId": request_id,
        "occurredAt": format_utc_millis(NOW),
        "payload": {"slotId": slot_id},
    }


def _invalid_barrier(request_id: str) -> dict[str, object]:
    return {
        "eventType": "INVALID_COMMAND",
        "version": "1",
        "requestId": request_id,
        "occurredAt": format_utc_millis(NOW),
        "payload": {},
    }


def _state_for(request_id: str) -> Callable[[dict[str, object]], bool]:
    return lambda message: (
        message.get("eventType") == "SUBSCRIPTION_STATE_CHANGED"
        and message.get("requestId") == request_id
    )


def _error_for(request_id: str) -> Callable[[dict[str, object]], bool]:
    return lambda message: (
        message.get("eventType") == "MARKET_DATA_ERROR" and message.get("requestId") == request_id
    )


def _candle_for(selection: MarketSelection) -> Callable[[dict[str, object]], bool]:
    def predicate(message: dict[str, object]) -> bool:
        if message.get("eventType") != "CANDLE_UPDATED":
            return False
        payload = message.get("payload")
        return isinstance(payload, dict) and payload.get("selection") == _selection_payload(
            selection
        )

    return predicate


def _payload(message: dict[str, object]) -> dict[str, object]:
    payload = message.get("payload")
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


async def _start_channel(
    provider: FakeRealtimeMarketProvider,
) -> tuple[_FakeWebSocket, asyncio.Task[None]]:
    channel = MarketDataChannel(
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
async def test_duplicate_subscribe_and_unsubscribe_commands_are_idempotent() -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task = await _start_channel(provider)
    subscribe = _subscribe("slot-1", FIVE_MINUTES, "req-subscribe")
    unsubscribe = _unsubscribe("slot-1", "req-unsubscribe")

    try:
        await websocket.feed_json(subscribe)
        await provider.wait_until_streaming(FIVE_MINUTES)
        await websocket.wait_for_message(_state_for("req-subscribe"))

        await websocket.feed_json(subscribe)
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-subscribe-again"))
        repeated_ack = await websocket.wait_for_message(_state_for("req-subscribe-again"))

        original_acks = [
            message for message in websocket.sent if _state_for("req-subscribe")(message)
        ]
        assert len(original_acks) == 1
        assert _payload(repeated_ack)["slotIds"] == ["slot-1"]
        assert provider.stream_calls.count(FIVE_MINUTES) == 1
        assert provider.release_calls == []

        await websocket.feed_json(unsubscribe)
        await websocket.feed_json(unsubscribe)
        await websocket.feed_json(_unsubscribe("slot-1", "req-unsubscribe-again"))

        await websocket.feed_json(_subscribe("slot-2", ONE_HOUR, "req-barrier"))
        await provider.wait_until_streaming(ONE_HOUR)
        await websocket.wait_for_message(_state_for("req-barrier"))

        assert provider.release_calls.count(FIVE_MINUTES) == 1
        assert FIVE_MINUTES not in provider.active_selections
        assert ONE_HOUR in provider.active_selections
    finally:
        await _stop_channel(websocket, channel_task)

    assert provider.release_calls.count(FIVE_MINUTES) == 1
    assert provider.release_calls.count(ONE_HOUR) == 1


@pytest.mark.asyncio
async def test_replacing_a_unique_slot_releases_old_and_acquires_new_once() -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task = await _start_channel(provider)

    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-five"))
        await provider.wait_until_streaming(FIVE_MINUTES)

        await websocket.feed_json(_subscribe("slot-1", ONE_HOUR, "req-replace"))
        await provider.wait_until_streaming(ONE_HOUR)
        replacement = await websocket.wait_for_message(_state_for("req-replace"))

        assert provider.stream_calls.count(FIVE_MINUTES) == 1
        assert provider.stream_calls.count(ONE_HOUR) == 1
        assert provider.release_calls.count(FIVE_MINUTES) == 1
        assert provider.active_selections == frozenset({ONE_HOUR})
        assert _payload(replacement)["selection"] == _selection_payload(ONE_HOUR)
        assert _payload(replacement)["slotIds"] == ["slot-1"]

        await websocket.feed_json(_unsubscribe("slot-1", "req-remove-new"))
        await websocket.feed_json(_invalid_barrier("req-remove-new-barrier"))
        await websocket.wait_for_message(_error_for("req-remove-new-barrier"))
        assert provider.active_selections == frozenset()
    finally:
        await _stop_channel(websocket, channel_task)

    assert provider.release_calls.count(FIVE_MINUTES) == 1
    assert provider.release_calls.count(ONE_HOUR) == 1


@pytest.mark.asyncio
async def test_shared_selection_survives_other_slot_replace_until_zero_references() -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task = await _start_channel(provider)

    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-slot-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        await websocket.feed_json(_subscribe("slot-2", FIVE_MINUTES, "req-slot-2"))
        shared = await websocket.wait_for_message(_state_for("req-slot-2"))
        assert _payload(shared)["slotIds"] == ["slot-1", "slot-2"]
        assert provider.stream_calls.count(FIVE_MINUTES) == 1

        await websocket.feed_json(_subscribe("slot-1", ONE_HOUR, "req-replace-slot-1"))
        await provider.wait_until_streaming(ONE_HOUR)
        await websocket.wait_for_message(_state_for("req-replace-slot-1"))

        assert provider.release_calls.count(FIVE_MINUTES) == 0
        assert provider.active_selections == frozenset({FIVE_MINUTES, ONE_HOUR})

        provider.publish(
            make_candle(
                NOW,
                selection=FIVE_MINUTES,
                closed=False,
                received_at=NOW + timedelta(seconds=1),
            ),
            occurred_at=NOW + timedelta(seconds=1),
        )
        await websocket.wait_for_message(_candle_for(FIVE_MINUTES))

        await websocket.feed_json(_unsubscribe("slot-1", "req-remove-slot-1"))
        await websocket.feed_json(_invalid_barrier("req-remove-slot-1-barrier"))
        await websocket.wait_for_message(_error_for("req-remove-slot-1-barrier"))
        assert provider.release_calls.count(FIVE_MINUTES) == 0
        assert provider.active_selections == frozenset({FIVE_MINUTES})

        provider.publish(
            make_candle(
                NOW + timedelta(minutes=5),
                selection=FIVE_MINUTES,
                closed=False,
                received_at=NOW + timedelta(minutes=5, seconds=1),
            ),
            occurred_at=NOW + timedelta(minutes=5, seconds=1),
        )
        await websocket.wait_for_message(_candle_for(FIVE_MINUTES), occurrence=2)

        await websocket.feed_json(_unsubscribe("slot-2", "req-remove-slot-2"))
        await websocket.feed_json(_invalid_barrier("req-remove-slot-2-barrier"))
        await websocket.wait_for_message(_error_for("req-remove-slot-2-barrier"))
        assert provider.active_selections == frozenset()
    finally:
        await _stop_channel(websocket, channel_task)

    assert provider.release_calls.count(FIVE_MINUTES) == 1
    assert provider.release_calls.count(ONE_HOUR) == 1
