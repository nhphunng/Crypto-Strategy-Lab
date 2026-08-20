from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Iterable
from contextlib import suppress
from datetime import datetime
from typing import Protocol, cast
from uuid import uuid4

from fastapi import APIRouter, WebSocket
from pydantic import TypeAdapter, ValidationError
from starlette.websockets import WebSocketDisconnect

from crypto_lab.api.schemas.market_data import (
    MarketDataCommandEnvelope,
    RetryMarketDataCommand,
    SubscribeMarketDataCommand,
    UnsubscribeMarketDataCommand,
    candle_to_dto,
)
from crypto_lab.application.chart_delivery.historical_backfill import (
    HistoricalCandleReader,
    HistoricalGapBackfillAdapter,
)
from crypto_lab.application.chart_delivery.stream_candles import (
    CandleDelivery,
    DeliveryEventType,
    StreamCandles,
)
from crypto_lab.application.chart_delivery.subscription_registry import (
    SubscriptionLimitExceeded,
    SubscriptionRegistry,
)
from crypto_lab.application.market_data.ports import (
    Clock,
    RealtimeMarketDataProvider,
)
from crypto_lab.application.market_data.recover_stream import RecoveryPolicy
from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.market_data.selection import ConnectionState, MarketSelection
from crypto_lab.infrastructure.observability.metrics import MarketDataMetrics

logger = logging.getLogger(__name__)
router = APIRouter()
_COMMAND_ADAPTER: TypeAdapter[MarketDataCommandEnvelope] = TypeAdapter(MarketDataCommandEnvelope)
DEFAULT_METRICS = MarketDataMetrics()
_RECOVERY_FAILURE_REASONS = {"MARKET_RECOVERY_EXHAUSTED", "MARKET_GAP_RECOVERY_FAILED"}


class ChannelSocket(Protocol):
    async def accept(
        self,
        subprotocol: str | None = None,
        headers: Iterable[tuple[bytes, bytes]] | None = None,
    ) -> None: ...

    async def receive_json(self, mode: str = "text") -> object: ...

    async def send_json(self, data: object, mode: str = "text") -> None: ...


class MarketDataChannel:
    def __init__(
        self,
        *,
        provider: RealtimeMarketDataProvider,
        clock: Clock,
        event_id_factory: Callable[[], str] = lambda: str(uuid4()),
        max_slots: int = 4,
        max_candles: int = 1_000,
        history: HistoricalCandleReader | None = None,
        recovery_policy: RecoveryPolicy | None = None,
        connection_id: str | None = None,
        metrics: MarketDataMetrics | None = None,
    ) -> None:
        self._clock = clock
        self._event_id_factory = event_id_factory
        self._connection_id = connection_id or str(uuid4())
        self._metrics = metrics or DEFAULT_METRICS
        self._registry = SubscriptionRegistry(max_slots=max_slots)
        self._streams = StreamCandles(
            provider,
            clock,
            max_candles=max_candles,
            history=history,
            recovery_policy=recovery_policy,
        )
        self._stream_tasks: dict[MarketSelection, asyncio.Task[None]] = {}
        self._selection_states: dict[MarketSelection, ConnectionState] = {}
        self._handled_request_ids: set[str] = set()
        self._send_lock = asyncio.Lock()
        self._opened_at: datetime | None = None

    async def run(self, websocket: ChannelSocket) -> None:
        await websocket.accept()
        self._opened_at = self._clock.now()
        self._metrics.clients_connected += 1
        self._log("market_data.connection_opened", clientsConnected=self._metrics.clients_connected)
        try:
            while True:
                raw = await websocket.receive_json()
                await self._handle_command(websocket, raw)
        except WebSocketDisconnect:
            pass
        finally:
            await self._release_all()
            self._metrics.clients_connected -= 1
            duration_ms = 0
            if self._opened_at is not None:
                duration_ms = int((self._clock.now() - self._opened_at).total_seconds() * 1000)
            self._log(
                "market_data.connection_closed",
                durationMs=duration_ms,
                clientsConnected=self._metrics.clients_connected,
                logicalSlots=self._metrics.logical_slots,
                uniqueSelections=self._metrics.unique_selections,
            )

    async def _handle_command(self, websocket: ChannelSocket, raw: object) -> None:
        try:
            command = _COMMAND_ADAPTER.validate_python(raw)
        except ValidationError:
            await self._send_invalid_command(websocket, raw)
            return

        if command.request_id in self._handled_request_ids:
            return
        self._handled_request_ids.add(command.request_id)

        if isinstance(command, SubscribeMarketDataCommand):
            await self._subscribe(websocket, command)
        elif isinstance(command, UnsubscribeMarketDataCommand):
            await self._unsubscribe(command.payload.slot_id)
        elif isinstance(command, RetryMarketDataCommand):
            await self._retry(websocket, command.payload.slot_id, command.request_id)

    async def _subscribe(
        self,
        websocket: ChannelSocket,
        command: SubscribeMarketDataCommand,
    ) -> None:
        payload = command.payload
        try:
            selection = MarketSelection(
                payload.selection.provider,
                payload.selection.pair,
                payload.selection.timeframe,
            )
            change = self._registry.bind(payload.slot_id, selection)
        except SubscriptionLimitExceeded as error:
            await self._send_error(
                websocket,
                slot_id=payload.slot_id,
                request_id=command.request_id,
                code=error.code,
                message="A dashboard can use at most four chart slots.",
                retryable=False,
            )
            return
        except ValueError:
            await self._send_error(
                websocket,
                slot_id=payload.slot_id,
                request_id=command.request_id,
                code="MARKET_PAIR_UNSUPPORTED",
                message="The requested market selection is not supported.",
                retryable=False,
            )
            return

        if change.released_selection is not None:
            await self._release_selection(change.released_selection)

        self._record_gauges()
        acquired = change.acquired_selection is not None
        released = change.released_selection is not None
        self._log(
            "market_data.subscribed",
            slotId=payload.slot_id,
            provider=payload.selection.provider,
            pair=payload.selection.pair,
            timeframe=payload.selection.timeframe,
            acquired=acquired,
            released=released,
            logicalSlots=self._metrics.logical_slots,
            uniqueSelections=self._metrics.unique_selections,
        )

        state = self._selection_states.get(selection, ConnectionState.LOADING)
        await self._send_state(
            websocket,
            selection,
            state,
            request_id=command.request_id,
        )
        if change.acquired_selection is not None:
            self._selection_states[selection] = ConnectionState.LOADING
            self._stream_tasks[selection] = asyncio.create_task(
                self._pump(websocket, selection),
                name=f"market-data:{selection.pair}:{selection.timeframe.value}",
            )

    async def _unsubscribe(self, slot_id: str) -> None:
        try:
            change = self._registry.unbind(slot_id)
        except ValueError:
            return
        self._record_gauges()
        if change.released_selection is not None:
            self._log(
                "market_data.unsubscribed",
                slotId=slot_id,
                provider=change.released_selection.provider.value,
                pair=change.released_selection.pair,
                timeframe=change.released_selection.timeframe.value,
                logicalSlots=self._metrics.logical_slots,
                uniqueSelections=self._metrics.unique_selections,
            )
            await self._release_selection(change.released_selection)

    async def _retry(
        self,
        websocket: ChannelSocket,
        slot_id: str,
        request_id: str,
    ) -> None:
        selection = self._registry.binding_for(slot_id)
        if selection is None:
            await self._send_error(
                websocket,
                slot_id=slot_id,
                request_id=request_id,
                code="MARKET_PAIR_UNSUPPORTED",
                message="The chart slot has no active market selection.",
                retryable=False,
            )
            return
        await self._release_selection(selection, preserve_binding=True)
        self._selection_states[selection] = ConnectionState.RECONNECTING
        self._metrics.reconnects += 1
        self._log(
            "market_data.retry",
            slotId=slot_id,
            provider=selection.provider.value,
            pair=selection.pair,
            timeframe=selection.timeframe.value,
            reconnects=self._metrics.reconnects,
        )
        await self._send_state(
            websocket,
            selection,
            ConnectionState.RECONNECTING,
            request_id=request_id,
        )
        self._stream_tasks[selection] = asyncio.create_task(
            self._pump(websocket, selection),
            name=f"market-data-retry:{selection.pair}:{selection.timeframe.value}",
        )

    async def _pump(self, websocket: ChannelSocket, selection: MarketSelection) -> None:
        async for delivery in self._streams.stream(selection):
            if not self._registry.slots_for(selection):
                return
            if delivery.event_type is DeliveryEventType.CANDLE:
                await self._send_candle(websocket, delivery)
            else:
                state = delivery.state
                if state is None:
                    continue
                self._selection_states[selection] = state
                if state is ConnectionState.RECONNECTING:
                    self._metrics.reconnects += 1
                if delivery.reason_code in _RECOVERY_FAILURE_REASONS:
                    self._metrics.recovery_failures += 1
                if delivery.last_event_at is not None:
                    age = (delivery.occurred_at or self._clock.now()) - delivery.last_event_at
                    self._metrics.last_event_age_seconds = max(0, age.total_seconds())
                await self._send_state(
                    websocket,
                    selection,
                    state,
                    occurred_at=delivery.occurred_at,
                    attempt=delivery.attempt,
                    reason_code=delivery.reason_code,
                    retry_after_ms=delivery.retry_after_ms or None,
                    last_event_at=delivery.last_event_at,
                )
                self._log_state(selection, state, delivery)

    async def _send_candle(
        self,
        websocket: ChannelSocket,
        delivery: CandleDelivery,
    ) -> None:
        candle = delivery.candle
        revision = delivery.revision
        if candle is None or revision is None:
            return
        duration_ms = max(0, int((self._clock.now() - delivery.occurred_at).total_seconds() * 1000))
        self._metrics.record_publish_latency_ms(duration_ms)
        await self._send(
            websocket,
            {
                "eventType": "CANDLE_UPDATED",
                "version": "1",
                "eventId": self._event_id_factory(),
                "occurredAt": format_utc_millis(delivery.occurred_at),
                "payload": {
                    "selection": self._selection_payload(delivery.selection),
                    "revision": revision,
                    "candle": candle_to_dto(candle).model_dump(
                        by_alias=True,
                        mode="json",
                    ),
                },
            },
        )

    async def _send_state(
        self,
        websocket: ChannelSocket,
        selection: MarketSelection,
        state: ConnectionState,
        *,
        request_id: str | None = None,
        occurred_at: datetime | None = None,
        attempt: int = 0,
        reason_code: str | None = None,
        retry_after_ms: int | None = None,
        last_event_at: datetime | None = None,
    ) -> None:
        timestamp = occurred_at or self._clock.now()
        event: dict[str, object] = {
            "eventType": "SUBSCRIPTION_STATE_CHANGED",
            "version": "1",
            "eventId": self._event_id_factory(),
            "occurredAt": format_utc_millis(timestamp),
            "payload": {
                "slotIds": list(self._registry.slots_for(selection)),
                "selection": self._selection_payload(selection),
                "state": state.value,
                "attempt": attempt,
                **({"retryAfterMs": retry_after_ms} if retry_after_ms is not None else {}),
                **(
                    {"lastEventAt": format_utc_millis(last_event_at)}
                    if last_event_at is not None
                    else {}
                ),
                **({"reasonCode": reason_code} if reason_code else {}),
            },
        }
        if request_id is not None:
            event["requestId"] = request_id
        await self._send(websocket, event)

    async def _send_invalid_command(self, websocket: ChannelSocket, raw: object) -> None:
        request_id: str | None = None
        slot_id: str | None = None
        code = "MARKET_REQUEST_MALFORMED"
        if isinstance(raw, dict):
            raw_request_id = raw.get("requestId")
            request_id = raw_request_id if isinstance(raw_request_id, str) else None
            raw_payload = raw.get("payload")
            if isinstance(raw_payload, dict) and isinstance(raw_payload.get("slotId"), str):
                slot_id = cast(str, raw_payload["slotId"])
            if raw.get("version") != "1":
                code = "MARKET_EVENT_VERSION_UNSUPPORTED"
        self._metrics.invalid_events += 1
        self._log(
            "market_data.invalid_command",
            code=code,
            slotId=slot_id,
            invalidEvents=self._metrics.invalid_events,
            level=logging.WARNING,
        )
        await self._send_error(
            websocket,
            slot_id=slot_id,
            request_id=request_id,
            code=code,
            message="The market-data command is invalid.",
            retryable=False,
        )

    async def _send_error(
        self,
        websocket: ChannelSocket,
        *,
        slot_id: str | None,
        request_id: str | None,
        code: str,
        message: str,
        retryable: bool,
    ) -> None:
        event: dict[str, object] = {
            "eventType": "MARKET_DATA_ERROR",
            "version": "1",
            "eventId": self._event_id_factory(),
            "occurredAt": format_utc_millis(self._clock.now()),
            "payload": {
                **({"slotId": slot_id} if slot_id else {}),
                "code": code,
                "message": message,
                "retryable": retryable,
            },
        }
        if request_id is not None:
            event["requestId"] = request_id
        await self._send(websocket, event)

    async def _send(self, websocket: ChannelSocket, event: dict[str, object]) -> None:
        async with self._send_lock:
            await websocket.send_json(event)

    async def _release_selection(
        self,
        selection: MarketSelection,
        *,
        preserve_binding: bool = False,
    ) -> None:
        task = self._stream_tasks.pop(selection, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._streams.release(selection)
        self._selection_states.pop(selection, None)
        if not preserve_binding:
            return

    async def _release_all(self) -> None:
        selections = self._registry.release_all()
        for task in self._stream_tasks.values():
            task.cancel()
        if self._stream_tasks:
            await asyncio.gather(*self._stream_tasks.values(), return_exceptions=True)
        self._stream_tasks.clear()
        for selection in selections:
            await self._streams.release(selection)
        self._selection_states.clear()
        self._record_gauges()

    def _record_gauges(self) -> None:
        self._metrics.logical_slots = self._registry.slot_count
        self._metrics.unique_selections = len(
            {binding.selection for binding in self._registry.bindings}
        )

    def _log_state(
        self,
        selection: MarketSelection,
        state: ConnectionState,
        delivery: CandleDelivery,
    ) -> None:
        fields: dict[str, object] = {
            "provider": selection.provider.value,
            "pair": selection.pair,
            "timeframe": selection.timeframe.value,
            "state": state.value,
            "attempt": delivery.attempt,
            "reconnects": self._metrics.reconnects,
        }
        if delivery.reason_code:
            fields["reasonCode"] = delivery.reason_code
        if delivery.retry_after_ms is not None:
            fields["retryAfterMs"] = delivery.retry_after_ms
        if delivery.last_event_at is not None:
            fields["lastEventAt"] = format_utc_millis(delivery.last_event_at)
        level = logging.INFO
        message = "market_data.state_changed"
        if delivery.reason_code in _RECOVERY_FAILURE_REASONS:
            level = logging.WARNING
            message = "market_data.recovery_failed"
            fields["recoveryFailures"] = self._metrics.recovery_failures
        self._log(message, level=level, **fields)

    def _log(self, message: str, *, level: int = logging.INFO, **fields: object) -> None:
        logger.log(
            level,
            message,
            extra={"fields": {"connectionId": self._connection_id, **fields}},
        )

    @staticmethod
    def _selection_payload(selection: MarketSelection) -> dict[str, str]:
        return {
            "provider": selection.provider.value,
            "pair": selection.pair,
            "timeframe": selection.timeframe.value,
        }


@router.websocket("/ws/v1/market-data")
async def market_data_websocket(websocket: WebSocket) -> None:
    container = websocket.app.state.container
    hub = container.realtime_hub
    provider = hub.client() if hub is not None else container.realtime_provider
    if provider is None:
        await websocket.accept()
        await websocket.close(code=1011, reason="Realtime market data is unavailable")
        return
    channel = MarketDataChannel(
        provider=provider,
        clock=container.clock,
        history=HistoricalGapBackfillAdapter(
            container.historical,
            limit=container.settings.max_range_candles,
        ),
        recovery_policy=RecoveryPolicy(
            max_attempts=container.settings.provider_reconnect_max_attempts,
            initial_delay_seconds=container.settings.provider_reconnect_initial_delay_seconds,
            max_delay_seconds=container.settings.provider_reconnect_max_delay_seconds,
            jitter_ratio=container.settings.provider_reconnect_jitter_ratio,
        ),
        max_slots=container.settings.max_chart_slots_per_connection,
        max_candles=container.settings.max_range_candles,
    )
    await channel.run(websocket)
