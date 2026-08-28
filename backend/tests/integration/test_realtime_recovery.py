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
from crypto_lab.application.chart_delivery.historical_backfill import (
    HistoricalGapBackfillAdapter,
)
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.market_data.recover_stream import RecoveryPolicy
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.domain.market_data.timeframe import Timeframe
from tests.fixtures.market_data import (
    FakeProvider,
    InMemoryMarketDataRepository,
    MutableClock,
    make_candle,
)
from tests.integration.fakes.fake_realtime_market_provider import (
    FakeRealtimeMarketProvider,
)

NOW = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)
FIVE_MINUTES = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
ONE_HOUR = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_HOUR)
EVENT_ADAPTER: TypeAdapter[MarketDataEventEnvelope] = TypeAdapter(MarketDataEventEnvelope)
_DISCONNECT = object()

FAST_RECOVERY = RecoveryPolicy(
    max_attempts=8,
    initial_delay_seconds=0.001,
    max_delay_seconds=0.001,
    jitter_ratio=0,
)
SHORT_BUDGET = RecoveryPolicy(
    max_attempts=2,
    initial_delay_seconds=0.001,
    max_delay_seconds=0.001,
    jitter_ratio=0,
)


class _Channel(Protocol):
    async def run(self, websocket: _FakeWebSocket) -> None: ...


class _ChannelFactory(Protocol):
    def __call__(
        self,
        *,
        provider: FakeRealtimeMarketProvider,
        clock: MutableClock,
        event_id_factory: Callable[[], str],
        history: object,
        recovery_policy: RecoveryPolicy,
    ) -> _Channel: ...


class _EventIds:
    def __init__(self) -> None:
        self._next = 1

    def __call__(self) -> str:
        value = f"evt-{self._next:03d}"
        self._next += 1
        return value


class _FakeWebSocket:
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
            "RED T041: the recovery integration tests require market_data_channel",
            pytrace=False,
        )

    channel_type = getattr(module, "MarketDataChannel", None)
    if channel_type is None:
        pytest.fail("RED T041: MarketDataChannel must exist", pytrace=False)

    def build(
        *,
        provider: FakeRealtimeMarketProvider,
        clock: MutableClock,
        event_id_factory: Callable[[], str],
        history: object,
        recovery_policy: RecoveryPolicy,
    ) -> _Channel:
        return cast(
            _Channel,
            channel_type(
                provider=provider,
                clock=clock,
                event_id_factory=event_id_factory,
                history=history,
                recovery_policy=recovery_policy,
            ),
        )

    return build


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


def _retry(slot_id: str, request_id: str) -> dict[str, object]:
    return {
        "eventType": "RETRY_MARKET_DATA",
        "version": "1",
        "requestId": request_id,
        "occurredAt": format_utc_millis(NOW),
        "payload": {"slotId": slot_id},
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
    history: object | None = None,
    recovery_policy: RecoveryPolicy = FAST_RECOVERY,
    clock: MutableClock | None = None,
) -> tuple[_FakeWebSocket, asyncio.Task[None], MutableClock]:
    mutable_clock = clock or MutableClock(NOW)
    channel = channel_factory(
        provider=provider,
        clock=mutable_clock,
        event_id_factory=_EventIds(),
        history=history or InMemoryMarketDataRepository(),
        recovery_policy=recovery_policy,
    )
    websocket = _FakeWebSocket()
    task = asyncio.create_task(channel.run(websocket))
    await websocket.wait_until_accepted()
    return websocket, task, mutable_clock


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


def _five_minutes(minute: int) -> datetime:
    return datetime(2026, 8, 13, 10, minute, tzinfo=UTC)


def _establish_live(
    websocket: _FakeWebSocket,
    provider: FakeRealtimeMarketProvider,
) -> None:
    """Publish open then closed candles through 10:10 so a checkpoint exists."""
    open_candle = make_candle(
        _five_minutes(0),
        selection=FIVE_MINUTES,
        close="101",
        closed=False,
        received_at=_five_minutes(0) + timedelta(seconds=1),
    )
    provider.publish(open_candle, occurred_at=open_candle.received_at)
    for minute, close in ((0, "101.25"), (5, "101.5"), (10, "101.75")):
        closed = make_candle(
            _five_minutes(minute),
            selection=FIVE_MINUTES,
            close=close,
            closed=True,
            received_at=_five_minutes(minute) + timedelta(seconds=2),
        )
        provider.publish(closed, occurred_at=closed.received_at)
    asyncio.get_running_loop().call_later(0.01, lambda: None)


@pytest.mark.asyncio
async def test_disconnect_marks_stale_then_reconnecting(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task, _ = await _start_channel(channel_factory, provider)
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))

        stale = await websocket.wait_for_message(_is_state(state="STALE"))
        assert _payload(stale)["reasonCode"] == "PROVIDER_DISCONNECTED"
        reconnecting = await websocket.wait_for_message(_is_state(state="RECONNECTING"))
        assert _payload(reconnecting)["attempt"] == 1
        assert _payload(reconnecting)["retryAfterMs"] > 0
        assert _payload(reconnecting)["lastEventAt"] == format_utc_millis(
            _five_minutes(10) + timedelta(seconds=2)
        )
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=2)
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_heartbeat_timeout_uses_provider_heartbeat_reason(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task, _ = await _start_channel(channel_factory, provider)
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(
            FIVE_MINUTES,
            occurred_at=_five_minutes(12),
            reason_code="PROVIDER_HEARTBEAT_TIMEOUT",
        )

        stale = await websocket.wait_for_message(_is_state(state="STALE"))
        assert _payload(stale)["reasonCode"] == "PROVIDER_HEARTBEAT_TIMEOUT"
        await websocket.wait_for_message(_is_state(state="RECONNECTING"))
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_gap_is_backfilled_before_live_with_exact_closed_intervals(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    history = InMemoryMarketDataRepository()
    for minute in (15, 20, 25):
        await history.store_closed_candles(
            (
                make_candle(
                    _five_minutes(minute),
                    selection=FIVE_MINUTES,
                    close=str(101 + minute / 100),
                    received_at=_five_minutes(minute) + timedelta(seconds=1),
                ),
            )
        )
    websocket, channel_task, clock = await _start_channel(
        channel_factory, provider, history=history
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="RECONNECTING"))
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=2)

        clock.advance(_five_minutes(30))
        provider.publish(
            make_candle(
                _five_minutes(30),
                selection=FIVE_MINUTES,
                high="104",
                close="103",
                closed=False,
                received_at=_five_minutes(30) + timedelta(seconds=1),
            ),
            occurred_at=_five_minutes(30) + timedelta(seconds=1),
        )

        recovered_t3 = await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=5)
        recovered_t4 = await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=6)
        recovered_t5 = await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=7)
        await websocket.wait_for_message(_is_state(state="LIVE"), occurrence=2)
        current_update = await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=8)

        candles = [
            message for message in websocket.sent if message.get("eventType") == "CANDLE_UPDATED"
        ]
        opens = [
            cast(dict[str, object], _payload(message)["candle"])["openTime"] for message in candles
        ]
        assert opens == [
            format_utc_millis(_five_minutes(0)),
            format_utc_millis(_five_minutes(0)),
            format_utc_millis(_five_minutes(5)),
            format_utc_millis(_five_minutes(10)),
            format_utc_millis(_five_minutes(15)),
            format_utc_millis(_five_minutes(20)),
            format_utc_millis(_five_minutes(25)),
            format_utc_millis(_five_minutes(30)),
        ]
        for update in (recovered_t3, recovered_t4, recovered_t5):
            assert _payload(update)["revision"] == 1
            assert cast(dict[str, object], _payload(update)["candle"])["closed"] is True
        assert cast(dict[str, object], _payload(current_update)["candle"])["closed"] is False

        live_messages = [message for message in websocket.sent if _is_state(state="LIVE")(message)]
        assert websocket.sent.index(live_messages[-1]) > websocket.sent.index(recovered_t5)
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_missing_gap_is_acquired_through_historical_use_case_before_live(
    channel_factory: _ChannelFactory,
) -> None:
    realtime_provider = FakeRealtimeMarketProvider()
    repository = InMemoryMarketDataRepository()
    missing = tuple(
        make_candle(
            _five_minutes(minute),
            selection=FIVE_MINUTES,
            close=str(101 + minute / 100),
            received_at=_five_minutes(minute) + timedelta(seconds=1),
        )
        for minute in (15, 20, 25)
    )
    historical_provider = FakeProvider(missing)
    clock = MutableClock(NOW)
    historical = HistoricalMarketDataService(repository, historical_provider, clock)
    history = HistoricalGapBackfillAdapter(historical, limit=1_000)
    websocket, channel_task, _ = await _start_channel(
        channel_factory,
        realtime_provider,
        history=history,
        clock=clock,
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await realtime_provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, realtime_provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        realtime_provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="RECONNECTING"))
        await realtime_provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=2)

        clock.advance(_five_minutes(30))
        realtime_provider.publish(
            make_candle(
                _five_minutes(30),
                selection=FIVE_MINUTES,
                closed=False,
                received_at=_five_minutes(30) + timedelta(seconds=1),
            ),
            occurred_at=_five_minutes(30) + timedelta(seconds=1),
        )

        await websocket.wait_for_message(_is_state(state="LIVE"), occurrence=2)
        assert len(historical_provider.calls) == 1
        assert historical_provider.calls[0].start_time == _five_minutes(15)
        assert historical_provider.calls[0].end_time == _five_minutes(30)
        stored = await repository.read_candles(FIVE_MINUTES, historical_provider.calls[0])
        assert stored == missing
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_incomplete_backfill_retries_until_complete(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    history = InMemoryMarketDataRepository()
    await history.store_closed_candles(
        (
            make_candle(
                _five_minutes(15),
                selection=FIVE_MINUTES,
                received_at=_five_minutes(15) + timedelta(seconds=1),
            ),
            make_candle(
                _five_minutes(25),
                selection=FIVE_MINUTES,
                received_at=_five_minutes(25) + timedelta(seconds=1),
            ),
        )
    )
    websocket, channel_task, clock = await _start_channel(
        channel_factory, provider, history=history
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="RECONNECTING"))
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=2)

        clock.advance(_five_minutes(30))
        provider.publish(
            make_candle(
                _five_minutes(30),
                selection=FIVE_MINUTES,
                closed=False,
                received_at=_five_minutes(30) + timedelta(seconds=1),
            ),
            occurred_at=_five_minutes(30) + timedelta(seconds=1),
        )

        gap_failed = await websocket.wait_for_message(_is_state(state="STALE"), occurrence=2)
        assert _payload(gap_failed)["reasonCode"] == "MARKET_GAP_RECOVERY_FAILED"
        await websocket.wait_for_message(_is_state(state="RECONNECTING"), occurrence=2)
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=3)

        await history.store_closed_candles(
            (
                make_candle(
                    _five_minutes(20),
                    selection=FIVE_MINUTES,
                    received_at=_five_minutes(20) + timedelta(seconds=1),
                ),
            )
        )
        provider.publish(
            make_candle(
                _five_minutes(30),
                selection=FIVE_MINUTES,
                high="105",
                close="104",
                closed=False,
                received_at=_five_minutes(30) + timedelta(seconds=2),
            ),
            occurred_at=_five_minutes(30) + timedelta(seconds=2),
        )

        await websocket.wait_for_message(_is_state(state="LIVE"), occurrence=2)
        candles = [
            message for message in websocket.sent if message.get("eventType") == "CANDLE_UPDATED"
        ]
        opens = [
            cast(dict[str, object], _payload(message)["candle"])["openTime"] for message in candles
        ]
        for minute in (15, 20, 25):
            assert format_utc_millis(_five_minutes(minute)) in opens
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_duplicate_recovery_and_live_replay_do_not_add_duplicates(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    history = InMemoryMarketDataRepository()
    await history.store_closed_candles(
        tuple(
            make_candle(
                _five_minutes(minute),
                selection=FIVE_MINUTES,
                close=str(101 + minute / 100),
                received_at=_five_minutes(minute) + timedelta(seconds=1),
            )
            for minute in (15, 20, 25)
        )
    )
    websocket, channel_task, clock = await _start_channel(
        channel_factory, provider, history=history
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="RECONNECTING"))
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=2)
        clock.advance(_five_minutes(30))
        provider.publish(
            make_candle(
                _five_minutes(30),
                selection=FIVE_MINUTES,
                closed=False,
                received_at=_five_minutes(30) + timedelta(seconds=1),
            ),
            occurred_at=_five_minutes(30) + timedelta(seconds=1),
        )
        await websocket.wait_for_message(_is_state(state="LIVE"), occurrence=2)

        replay_closed_t5 = make_candle(
            _five_minutes(25),
            selection=FIVE_MINUTES,
            close="101.25",
            received_at=_five_minutes(25) + timedelta(seconds=2),
        )
        provider.publish(replay_closed_t5, occurred_at=replay_closed_t5.received_at)

        await asyncio.sleep(0.05)
        candles = [
            message for message in websocket.sent if message.get("eventType") == "CANDLE_UPDATED"
        ]
        opens = [
            cast(dict[str, object], _payload(message)["candle"])["openTime"] for message in candles
        ]
        t0 = format_utc_millis(_five_minutes(0))
        t25 = format_utc_millis(_five_minutes(25))
        assert opens.count(t25) == 1
        assert len(opens) == 8
        others = [open_time for open_time in opens if open_time != t0]
        assert len(others) == len(set(others))
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_exhaustion_emits_error_with_exhausted_reason(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task, _ = await _start_channel(
        channel_factory, provider, recovery_policy=SHORT_BUDGET
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        for generation in (1, 2):
            provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
            await websocket.wait_for_message(_is_state(state="STALE"))
            await websocket.wait_for_message(_is_state(state="RECONNECTING"))
            await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=generation + 1)

        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="STALE"), occurrence=3)
        error = await websocket.wait_for_message(_is_state(state="ERROR"))
        assert _payload(error)["reasonCode"] == "MARKET_RECOVERY_EXHAUSTED"
        assert _payload(error)["attempt"] == 2
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_manual_retry_after_exhaustion_resets_the_budget(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task, _ = await _start_channel(
        channel_factory, provider, recovery_policy=SHORT_BUDGET
    )
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        _establish_live(websocket, provider)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        for generation in (1, 2):
            provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
            await websocket.wait_for_message(_is_state(state="STALE"))
            await websocket.wait_for_message(_is_state(state="RECONNECTING"))
            await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=generation + 1)
        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="ERROR"))

        await websocket.feed_json(_retry("slot-1", "req-retry"))
        await websocket.wait_for_message(_is_state(state="RECONNECTING", request_id="req-retry"))
        await provider.wait_until_streaming(FIVE_MINUTES, minimum_calls=4)
        provider.publish(
            make_candle(
                _five_minutes(30),
                selection=FIVE_MINUTES,
                high="105",
                close="104",
                closed=False,
                received_at=_five_minutes(30) + timedelta(seconds=1),
            ),
            occurred_at=_five_minutes(30) + timedelta(seconds=1),
        )
        live = await websocket.wait_for_message(_is_state(state="LIVE"), occurrence=2)
        assert _payload(live)["attempt"] == 0
    finally:
        await _stop_channel(websocket, channel_task)


@pytest.mark.asyncio
async def test_recovery_affects_only_the_failed_selection(
    channel_factory: _ChannelFactory,
) -> None:
    provider = FakeRealtimeMarketProvider()
    websocket, channel_task, _ = await _start_channel(channel_factory, provider)
    try:
        await websocket.feed_json(_subscribe("slot-1", FIVE_MINUTES, "req-1"))
        await websocket.feed_json(_subscribe("slot-2", ONE_HOUR, "req-2"))
        await provider.wait_until_streaming(FIVE_MINUTES)
        await provider.wait_until_streaming(ONE_HOUR)
        _establish_live(websocket, provider)
        one_hour_candle = make_candle(
            NOW,
            selection=ONE_HOUR,
            open="49900",
            high="50500",
            low="49000",
            close="50000",
            closed=False,
            received_at=NOW + timedelta(seconds=1),
        )
        provider.publish(one_hour_candle, occurred_at=one_hour_candle.received_at)
        await websocket.wait_for_message(_is_state(state="LIVE"))

        provider.disconnect(FIVE_MINUTES, occurred_at=_five_minutes(12))
        await websocket.wait_for_message(_is_state(state="STALE"))

        states = [
            message
            for message in websocket.sent
            if message.get("eventType") == "SUBSCRIPTION_STATE_CHANGED"
        ]
        one_hour_states = [
            _payload(message)["state"]
            for message in states
            if cast(dict[str, object], _payload(message)["selection"])["timeframe"] == "1h"
        ]
        assert "STALE" not in one_hour_states
        assert "RECONNECTING" not in one_hour_states

        affected = _payload(states[-1])["slotIds"]
        assert affected == ["slot-1"]

        one_hour_live_after = make_candle(
            NOW,
            selection=ONE_HOUR,
            open="50000",
            high="50500",
            low="49000",
            close="50050",
            closed=False,
            received_at=NOW + timedelta(seconds=3),
        )
        provider.publish(one_hour_live_after, occurred_at=one_hour_live_after.received_at)
        await websocket.wait_for_message(_is_event("CANDLE_UPDATED"), occurrence=2)
    finally:
        await _stop_channel(websocket, channel_task)
