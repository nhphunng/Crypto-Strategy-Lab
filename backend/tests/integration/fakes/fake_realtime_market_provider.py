"""Deterministic, provider-neutral realtime adapter for integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime

from crypto_lab.application.market_data.ports import (
    RealtimeProviderEvent,
    RealtimeProviderEventType,
)
from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.selection import MarketSelection

_END_OF_STREAM = object()


@dataclass(slots=True)
class _Channel:
    queue: asyncio.Queue[RealtimeProviderEvent | object] = field(default_factory=asyncio.Queue)
    closed: bool = False


class FakeRealtimeMarketProvider:
    """A controllable structural implementation of the realtime provider port.

    Controls enqueue events synchronously, so a test decides the exact event order without
    sleeps or wall-clock access. ``disconnect`` and ``release`` terminate the current stream
    generation; a later ``stream`` call receives a fresh generation.
    """

    def __init__(self, provider: str = "BINANCE") -> None:
        self.provider = provider
        self.stream_calls: list[MarketSelection] = []
        self.release_calls: list[MarketSelection] = []
        self.events: list[RealtimeProviderEvent] = []
        self._channels: dict[MarketSelection, _Channel] = {}
        self._active_channels: dict[MarketSelection, _Channel] = {}
        self._last_closed: dict[MarketSelection, datetime] = {}
        self._stream_started = asyncio.Condition()

    def last_closed_checkpoint(self, selection: MarketSelection) -> datetime | None:
        return self._last_closed.get(selection)

    @property
    def active_selections(self) -> frozenset[MarketSelection]:
        return frozenset(self._active_channels)

    async def wait_until_streaming(
        self,
        selection: MarketSelection,
        *,
        minimum_calls: int = 1,
    ) -> None:
        """Wait until ``stream`` has been entered the requested number of times."""

        self._validate_selection(selection)
        if minimum_calls < 1:
            raise ValueError("minimum_calls must be positive")
        async with self._stream_started:
            await self._stream_started.wait_for(
                lambda: self.stream_calls.count(selection) >= minimum_calls
            )

    async def stream(
        self,
        selection: MarketSelection,
    ) -> AsyncIterator[RealtimeProviderEvent]:
        self._validate_selection(selection)
        if selection in self._active_channels:
            raise RuntimeError("selection already has an active fake provider stream")

        channel = self._channels.setdefault(selection, _Channel())
        self._active_channels[selection] = channel
        async with self._stream_started:
            self.stream_calls.append(selection)
            self._stream_started.notify_all()

        try:
            while True:
                item = await channel.queue.get()
                if item is _END_OF_STREAM:
                    break
                if not isinstance(item, RealtimeProviderEvent):
                    raise AssertionError("fake realtime channel contained an invalid item")
                yield item
        finally:
            if self._active_channels.get(selection) is channel:
                self._active_channels.pop(selection)
            if self._channels.get(selection) is channel and channel.closed:
                self._channels.pop(selection)

    async def release(self, selection: MarketSelection) -> None:
        self._validate_selection(selection)
        self.release_calls.append(selection)
        channel = self._channels.get(selection) or self._active_channels.get(selection)
        if channel is None or channel.closed:
            return
        self._close_channel(selection, channel)

    def publish(
        self,
        candle: Candle,
        *,
        occurred_at: datetime | None = None,
    ) -> RealtimeProviderEvent:
        """Queue one normalized Candle event and return it for direct assertions."""

        selection = candle.selection
        self._validate_selection(selection)
        event = RealtimeProviderEvent(
            event_type=RealtimeProviderEventType.CANDLE,
            selection=selection,
            occurred_at=occurred_at or candle.received_at,
            candle=candle,
        )
        if candle.closed:
            self._last_closed[selection] = candle.open_time
        self._enqueue(event)
        return event

    def heartbeat(
        self,
        selection: MarketSelection,
        *,
        occurred_at: datetime,
    ) -> RealtimeProviderEvent:
        """Queue a provider heartbeat at the test-controlled timestamp."""

        self._validate_selection(selection)
        event = RealtimeProviderEvent(
            event_type=RealtimeProviderEventType.HEARTBEAT,
            selection=selection,
            occurred_at=occurred_at,
        )
        self._enqueue(event)
        return event

    def disconnect(
        self,
        selection: MarketSelection,
        *,
        occurred_at: datetime,
        reason_code: str = "PROVIDER_DISCONNECTED",
    ) -> RealtimeProviderEvent:
        """Queue a terminal disconnect event and close that stream generation."""

        self._validate_selection(selection)
        event = RealtimeProviderEvent(
            event_type=RealtimeProviderEventType.DISCONNECTED,
            selection=selection,
            occurred_at=occurred_at,
            reason_code=reason_code,
        )
        channel = self._open_channel(selection)
        self.events.append(event)
        channel.queue.put_nowait(event)
        self._close_channel(selection, channel)
        return event

    def _enqueue(self, event: RealtimeProviderEvent) -> None:
        channel = self._open_channel(event.selection)
        self.events.append(event)
        channel.queue.put_nowait(event)

    def _open_channel(self, selection: MarketSelection) -> _Channel:
        channel = self._channels.setdefault(selection, _Channel())
        if channel.closed:
            raise RuntimeError("fake provider stream generation is already closed")
        return channel

    def _close_channel(self, selection: MarketSelection, channel: _Channel) -> None:
        channel.closed = True
        channel.queue.put_nowait(_END_OF_STREAM)
        if self._active_channels.get(selection) is channel:
            self._active_channels.pop(selection)
            self._channels.pop(selection, None)

    def _validate_selection(self, selection: MarketSelection) -> None:
        if selection.provider != self.provider:
            raise ValueError("selection provider does not match fake provider")
