from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

from crypto_lab.application.market_data.ports import (
    RealtimeMarketDataProvider,
    RealtimeProviderEvent,
)
from crypto_lab.domain.market_data.selection import MarketSelection

_END: Final = object()


@dataclass(slots=True)
class _SharedSelection:
    subscribers: dict[object, asyncio.Queue[RealtimeProviderEvent | object]] = field(
        default_factory=dict
    )
    task: asyncio.Task[None] | None = None


class RealtimeSelectionClient:
    """Connection-scoped provider view backed by the process-wide selection hub."""

    provider: str

    def __init__(self, hub: RealtimeSelectionHub) -> None:
        self._hub = hub
        self.provider = hub.provider
        self._tokens: dict[MarketSelection, object] = {}

    def stream(
        self,
        selection: MarketSelection,
    ) -> AsyncGenerator[RealtimeProviderEvent, None]:
        return self._stream(selection)

    async def _stream(
        self,
        selection: MarketSelection,
    ) -> AsyncGenerator[RealtimeProviderEvent, None]:
        if selection in self._tokens:
            raise RuntimeError("selection already has an active client stream")
        token, queue = await self._hub._subscribe(selection)
        self._tokens[selection] = token
        try:
            while True:
                item = await queue.get()
                if item is _END:
                    return
                if not isinstance(item, RealtimeProviderEvent):
                    raise AssertionError("selection hub delivered an invalid event")
                yield item
        finally:
            if self._tokens.get(selection) is token:
                await self._hub._unsubscribe(selection, token)
                self._tokens.pop(selection, None)

    async def release(self, selection: MarketSelection) -> None:
        token = self._tokens.pop(selection, None)
        if token is not None:
            await self._hub._unsubscribe(selection, token)

    def last_closed_checkpoint(self, selection: MarketSelection) -> datetime | None:
        return self._hub.last_closed_checkpoint(selection)


class RealtimeSelectionHub:
    """Fan out one upstream provider stream per selection to dashboard clients."""

    def __init__(self, upstream: RealtimeMarketDataProvider) -> None:
        self.provider = upstream.provider
        self._upstream = upstream
        self._selections: dict[MarketSelection, _SharedSelection] = {}
        self._lock = asyncio.Lock()
        self._closed = False

    def client(self) -> RealtimeSelectionClient:
        if self._closed:
            raise RuntimeError("selection hub is closed")
        return RealtimeSelectionClient(self)

    def last_closed_checkpoint(self, selection: MarketSelection) -> datetime | None:
        return self._upstream.last_closed_checkpoint(selection)

    async def _subscribe(
        self,
        selection: MarketSelection,
    ) -> tuple[object, asyncio.Queue[RealtimeProviderEvent | object]]:
        token = object()
        queue: asyncio.Queue[RealtimeProviderEvent | object] = asyncio.Queue()
        async with self._lock:
            if self._closed:
                raise RuntimeError("selection hub is closed")
            shared = self._selections.setdefault(selection, _SharedSelection())
            shared.subscribers[token] = queue
            if shared.task is None:
                shared.task = asyncio.create_task(
                    self._pump(selection, shared),
                    name=f"market-provider:{selection.pair}:{selection.timeframe.value}",
                )
        return token, queue

    async def _unsubscribe(self, selection: MarketSelection, token: object) -> None:
        task: asyncio.Task[None] | None = None
        async with self._lock:
            shared = self._selections.get(selection)
            if shared is None or shared.subscribers.pop(token, None) is None:
                return
            if shared.subscribers:
                return
            self._selections.pop(selection, None)
            task = shared.task
        if task is not None and task is not asyncio.current_task():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._upstream.release(selection)

    async def _pump(
        self,
        selection: MarketSelection,
        shared: _SharedSelection,
    ) -> None:
        stream = self._upstream.stream(selection)
        try:
            async for event in stream:
                async with self._lock:
                    queues = tuple(shared.subscribers.values())
                for queue in queues:
                    queue.put_nowait(event)
        finally:
            await stream.aclose()
            async with self._lock:
                queues = tuple(shared.subscribers.values())
            for queue in queues:
                queue.put_nowait(_END)

    async def close(self) -> None:
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            selections = tuple(self._selections.items())
            self._selections.clear()
        for selection, shared in selections:
            if shared.task is not None:
                shared.task.cancel()
                with suppress(asyncio.CancelledError):
                    await shared.task
            await self._upstream.release(selection)
            for queue in shared.subscribers.values():
                queue.put_nowait(_END)
