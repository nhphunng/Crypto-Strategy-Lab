from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from starlette.websockets import WebSocketDisconnect

from crypto_lab.api.websocket.market_data_channel import MarketDataChannel
from crypto_lab.application.market_data.recover_stream import RecoveryPolicy
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.observability.metrics import MarketDataMetrics
from tests.fixtures.market_data import FixedClock, make_candle
from tests.integration.fakes.fake_realtime_market_provider import (
    FakeRealtimeMarketProvider,
)

NOW = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
FIVE_MINUTES = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
ONE_HOUR = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_HOUR)
SHORT_BUDGET = RecoveryPolicy(
    max_attempts=2,
    initial_delay_seconds=0.001,
    max_delay_seconds=0.001,
    jitter_ratio=0,
)
_DISCONNECT = object()


class _EventIds:
    def __init__(self) -> None:
        self._next = 1

    def __call__(self) -> str:
        event_id = f"observability-event-{self._next}"
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
        "payload": {"slotId": slot_id, "generation": 1, "selection": _selection_payload(selection)},
    }


def _payload(message: dict[str, object]) -> dict[str, object]:
    payload = message.get("payload")
    assert isinstance(payload, dict)
    return cast(dict[str, object], payload)


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


def _is_event(event_type: str) -> Callable[[dict[str, object]], bool]:
    return lambda message: message.get("eventType") == event_type


async def _start_channel(
    provider: FakeRealtimeMarketProvider,
    metrics: MarketDataMetrics,
    *,
    connection_id: str = "conn-1",
    history: object | None = None,
    recovery_policy: RecoveryPolicy = SHORT_BUDGET,
) -> tuple[_FakeWebSocket, asyncio.Task[None]]:
    channel = MarketDataChannel(
        provider=provider,
        clock=FixedClock(NOW),
        event_id_factory=_EventIds(),
        metrics=metrics,
        connection_id=connection_id,
        recovery_policy=recovery_policy,
        **({"history": history} if history is not None else {}),
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


def _establish_live(
    websocket: _FakeWebSocket,
    provider: FakeRealtimeMarketProvider,
) -> None:
    open_candle = make_candle(
        NOW,
        selection=FIVE_MINUTES,
        close="101",
        closed=False,
        received_at=NOW + timedelta(seconds=1),
    )
    provider.publish(open_candle, occurred_at=open_candle.received_at)
    for minute, close in ((0, "101.25"), (5, "101.5"), (10, "101.75")):
        closed = make_candle(
            NOW + timedelta(minutes=minute),
            selection=FIVE_MINUTES,
            close=close,
            closed=True,
            received_at=NOW + timedelta(minutes=minute, seconds=2),
        )
        provider.publish(closed, occurred_at=closed.received_at)
    asyncio.get_running_loop().call_later(0.01, lambda: None)


@pytest.mark.asyncio
async def test_metrics_track_clients_slots_and_unique_selections() -> None:
    provider = FakeRealtimeMarketProvider()
    metrics = MarketDataMetrics()
    websocket, channel_task = await _start_channel(provider, metrics)
    try:
        assert metrics.clients_connected == 1

        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        await websocket.feed_json(_subscribe("slot-2", FIVE_MINUTES, "req-2"))
        await websocket.wait_for_message(_is_state(request_id="req-2"))
        await websocket.feed_json(_subscribe("slot-3", ONE_HOUR, "req-3"))
        await provider.wait_until_streaming(ONE_HOUR)
        await websocket.wait_for_message(_is_state(request_id="req-3"))

        assert metrics.logical_slots == 3
        assert metrics.unique_selections == 2

        await websocket.feed_json(_subscribe("slot-1", ONE_HOUR, "req-replace"))
        await websocket.wait_for_message(_is_state(request_id="req-replace"))
        assert metrics.logical_slots == 3
        assert metrics.unique_selections == 2
        await websocket.feed_json(_subscribe("slot-2", ONE_HOUR, "req-replace-2"))
        await websocket.wait_for_message(_is_state(request_id="req-replace-2"))
        assert metrics.logical_slots == 3
        assert metrics.unique_selections == 1
    finally:
        await _stop_channel(websocket, channel_task)

    assert metrics.clients_connected == 0
    assert metrics.logical_slots == 0
    assert metrics.unique_selections == 0


@pytest.mark.asyncio
async def test_reconnect_and_recovery_failure_counters() -> None:
    provider = FakeRealtimeMarketProvider()
    metrics = MarketDataMetrics()
    websocket, channel_task = await _start_channel(provider, metrics)
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        for generation in (1, 2):
            provider.disconnect(FIVE_MINUTES, occurred_at=NOW + timedelta(minutes=12))
            await websocket.wait_for_message(_is_state(state="STALE"))
            await websocket.wait_for_message(_is_state(state="RECONNECTING"))
            await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=generation + 1)

        provider.disconnect(FIVE_MINUTES, occurred_at=NOW + timedelta(minutes=12))
        await websocket.wait_for_message(_is_state(state="ERROR"))

        assert metrics.reconnects == 2
        assert metrics.recovery_failures == 1
        assert metrics.last_event_age_seconds is not None
        assert metrics.last_event_age_seconds >= 0
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_gap_recovery_failure_increments_recovery_failures() -> None:
    from tests.fixtures.market_data import InMemoryMarketDataRepository

    provider = FakeRealtimeMarketProvider()
    metrics = MarketDataMetrics()
    history = InMemoryMarketDataRepository()
    for minute in (15, 25):
        await history.store_closed_candles(
            (
                make_candle(
                    NOW + timedelta(minutes=minute),
                    selection=FIVE_MINUTES,
                    received_at=NOW + timedelta(minutes=minute, seconds=1),
                ),
            )
        )
    websocket, channel_task = await _start_channel(
        provider,
        metrics,
        history=history,
        recovery_policy=RecoveryPolicy(
            max_attempts=8,
            initial_delay_seconds=0.001,
            max_delay_seconds=0.001,
            jitter_ratio=0,
        ),
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(FIVE_MINUTES, occurred_at=NOW + timedelta(minutes=12))
        await websocket.wait_for_message(_is_state(state="RECONNECTING"))
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=2)

        provider.publish(
            make_candle(
                NOW + timedelta(minutes=30),
                selection=FIVE_MINUTES,
                closed=False,
                received_at=NOW + timedelta(minutes=30, seconds=1),
            ),
            occurred_at=NOW + timedelta(minutes=30, seconds=1),
        )
        gap_failed = await websocket.wait_for_message(_is_state(state="STALE"), occurrence=2)
        assert _payload(gap_failed)["reasonCode"] == "MARKET_GAP_RECOVERY_FAILED"
        assert metrics.recovery_failures == 1
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_invalid_command_increments_invalid_events() -> None:
    provider = FakeRealtimeMarketProvider()
    metrics = MarketDataMetrics()
    websocket, channel_task = await _start_channel(provider, metrics)
    try:
        await websocket.feed_json({"eventType": "SUBSCRIBE_MARKET_DATA", "version": "1"})
        error = await websocket.wait_for_message(_is_event("MARKET_DATA_ERROR"))
        assert _payload(error)["code"] == "MARKET_REQUEST_MALFORMED"
        assert metrics.invalid_events == 1
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_publish_latency_is_recorded() -> None:
    provider = FakeRealtimeMarketProvider()
    metrics = MarketDataMetrics()
    websocket, channel_task = await _start_channel(provider, metrics)
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        provider.publish(
            make_candle(
                NOW,
                selection=FIVE_MINUTES,
                closed=False,
                received_at=NOW - timedelta(seconds=2),
            ),
            occurred_at=NOW - timedelta(seconds=2),
        )
        await websocket.wait_for_message(_is_event("CANDLE_UPDATED"))
        assert metrics.publish_latency_ms_count == 1
        assert metrics.publish_latency_ms_total == 2000
        assert metrics.publish_latency_ms_max == 2000
        snapshot = metrics.snapshot()
        assert snapshot["publishLatencyMs"]["count"] == 1
        assert snapshot["publishLatencyMs"]["max"] == 2000
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_lifecycle_logs_are_sanitized_and_carry_connection_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = FakeRealtimeMarketProvider()
    metrics = MarketDataMetrics()
    caplog.set_level(logging.INFO, logger="crypto_lab.api.websocket.market_data_channel")
    websocket, channel_task = await _start_channel(provider, metrics)
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        await websocket.feed_json({"eventType": "SUBSCRIBE_MARKET_DATA", "version": "1"})
        await websocket.wait_for_message(_is_event("MARKET_DATA_ERROR"))
    finally:
        await _stop_channel(websocket, channel_task)

    records = [record for record in caplog.records if getattr(record, "fields", None) is not None]
    assert any(record.getMessage() == "market_data.connection_opened" for record in records)
    assert any(record.getMessage() == "market_data.connection_closed" for record in records)
    assert any(record.getMessage() == "market_data.invalid_command" for record in records)

    opened = next(
        record for record in records if record.getMessage() == "market_data.connection_opened"
    )
    fields = cast(dict[str, object], opened.fields)
    assert fields["connectionId"] == "conn-1"
    assert fields["clientsConnected"] == 1

    subscribed = next(
        record for record in records if record.getMessage() == "market_data.subscribed"
    )
    fields = cast(dict[str, object], subscribed.fields)
    assert fields["connectionId"] == "conn-1"
    assert fields["slotId"] == "slot-1"
    assert fields["pair"] == "BTCUSDT"
    assert fields["timeframe"] == "5m"

    forbidden = {"candle", "payload", "raw", "message", "event"}
    for record in records:
        for key in cast(dict[str, object], record.fields):
            assert key not in forbidden, f"log field {key} is not sanitized"
