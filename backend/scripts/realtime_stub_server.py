"""Deterministic local backend for load and smoke validation.

Runs the real FastAPI app with an in-process provider stub that publishes one
accepted candle update per second per active selection plus periodic heartbeats,
so `tests/load/realtime-market-data.js` can be exercised without Binance or a
database.

Usage (from the repository root):

    backend/.venv/Scripts/python.exe backend/scripts/realtime_stub_server.py

Then run k6 in another terminal:

    k6 run tests/load/realtime-market-data.js
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Protocol

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_ROOT / "src"))

import uvicorn  # noqa: E402

from crypto_lab.api.dependencies import Container, SystemClock  # noqa: E402
from crypto_lab.application.market_data.dataset_service import DatasetService  # noqa: E402
from crypto_lab.application.market_data.historical_service import (  # noqa: E402
    HistoricalMarketDataService,
)
from crypto_lab.application.market_data.ports import (  # noqa: E402
    RealtimeProviderEvent,
    RealtimeProviderEventType,
)
from crypto_lab.domain.market_data.candle import Candle  # noqa: E402
from crypto_lab.domain.market_data.selection import MarketSelection  # noqa: E402
from crypto_lab.infrastructure.settings import Settings  # noqa: E402
from crypto_lab.main import create_app  # noqa: E402

_END_OF_STREAM = object()


class Clock(Protocol):
    def now(self) -> datetime: ...


class _Publisher:
    """One autonomous stream generator per selection with per-consumer fan-out.

    The real Binance provider keeps one upstream stream per selection and serves
    every subscribed channel from it; this stub mirrors that with a refcounted
    source. Each ``stream`` call registers its own consumer queue so concurrent
    channels never steal each other's events.
    """

    def __init__(self, selection: MarketSelection, clock: Clock) -> None:
        self.selection = selection
        self._clock = clock
        self._subscribers: set[asyncio.Queue[RealtimeProviderEvent | object]] = set()
        self._task: asyncio.Task[None] | None = None
        self._last_bucket: datetime | None = None
        self._revision = 0
        self._last_closed: datetime | None = None
        self.refcount = 0

    def acquire(self) -> asyncio.Queue[RealtimeProviderEvent | object]:
        self.refcount += 1
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(
                self._run(), name=f"stub-provider:{self.selection}"
            )
        queue: asyncio.Queue[RealtimeProviderEvent | object] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def detach(self, queue: asyncio.Queue[RealtimeProviderEvent | object]) -> None:
        self._subscribers.discard(queue)

    async def stop(self) -> None:
        self.refcount = 0
        for queue in tuple(self._subscribers):
            queue.put_nowait(_END_OF_STREAM)
        self._subscribers.clear()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def last_closed_checkpoint(self) -> datetime | None:
        return self._last_closed

    async def _run(self) -> None:
        ticks_since_heartbeat = 0
        while True:
            now = self._clock.now()
            bucket = self.selection.timeframe.floor(now)
            if self._last_bucket is None:
                self._last_bucket = bucket
                self._emit(self._open_candle(bucket))
            elif bucket != self._last_bucket:
                self._emit(self._closed_candle(self._last_bucket))
                self._last_bucket = bucket
                self._revision = 0
                self._emit(self._open_candle(bucket))
            else:
                self._revision += 1
                self._emit(self._open_candle(bucket))
            ticks_since_heartbeat += 1
            if ticks_since_heartbeat >= 15:
                ticks_since_heartbeat = 0
                self._emit(
                    RealtimeProviderEvent(
                        event_type=RealtimeProviderEventType.HEARTBEAT,
                        selection=self.selection,
                        occurred_at=self._clock.now(),
                    )
                )
            await asyncio.sleep(1)

    def _emit(self, candle_or_heartbeat: RealtimeProviderEvent) -> None:
        for queue in tuple(self._subscribers):
            queue.put_nowait(candle_or_heartbeat)
        if candle_or_heartbeat.candle is not None and candle_or_heartbeat.candle.closed:
            self._last_closed = candle_or_heartbeat.candle.open_time

    def _open_candle(self, bucket: datetime) -> RealtimeProviderEvent:
        drift = Decimal(self._revision) * Decimal("0.25")
        base = 50000 + (self.selection.timeframe.value.encode()[0] * 13) % 4000
        close = Decimal(base) + drift
        return self._event(
            self._make(
                bucket,
                open_value=Decimal(base) + drift,
                close=close,
                closed=False,
            )
        )

    def _closed_candle(self, bucket: datetime) -> RealtimeProviderEvent:
        return self._event(
            self._make(bucket, open_value=Decimal(50000), close=Decimal(50250), closed=True)
        )

    def _event(self, candle: Candle) -> RealtimeProviderEvent:
        return RealtimeProviderEvent(
            event_type=RealtimeProviderEventType.CANDLE,
            selection=self.selection,
            occurred_at=self._clock.now(),
            candle=candle,
        )

    def _make(
        self,
        bucket: datetime,
        *,
        open_value: Decimal,
        close: Decimal,
        closed: bool,
    ) -> Candle:
        return Candle(
            provider=self.selection.provider,
            pair=self.selection.pair,
            timeframe=self.selection.timeframe,
            open_time=bucket,
            close_time=self.selection.timeframe.close_time(bucket),
            open=open_value,
            high=max(open_value, close) + Decimal("10"),
            low=min(open_value, close) - Decimal("10"),
            close=close,
            volume=Decimal(self._revision + 1) * Decimal("1.5"),
            closed=closed,
            received_at=self._clock.now(),
        )


class StubRealtimeProvider:
    provider = "BINANCE"

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._publishers: dict[MarketSelection, _Publisher] = {}

    async def stream(
        self,
        selection: MarketSelection,
    ) -> AsyncIterator[RealtimeProviderEvent]:
        publisher = self._publishers.setdefault(
            selection, _Publisher(selection, self._clock)
        )
        queue = publisher.acquire()
        try:
            while True:
                item = await queue.get()
                if item is _END_OF_STREAM:
                    break
                assert isinstance(item, RealtimeProviderEvent)
                yield item
        finally:
            publisher.detach(queue)

    async def release(self, selection: MarketSelection) -> None:
        publisher = self._publishers.get(selection)
        if publisher is None:
            return
        publisher.refcount = max(0, publisher.refcount - 1)
        if publisher.refcount == 0:
            await publisher.stop()
            self._publishers.pop(selection, None)

    def last_closed_checkpoint(self, selection: MarketSelection) -> datetime | None:
        publisher = self._publishers.get(selection)
        return publisher.last_closed_checkpoint() if publisher is not None else None


class StubHistoricalProvider:
    provider = "BINANCE"

    async def iter_historical(
        self,
        selection: MarketSelection,
        time_range: object,
    ) -> AsyncIterator[tuple[Candle, ...]]:
        del selection, time_range
        if False:
            yield ()


class StubRepository:
    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: object,
    ) -> tuple[Candle, ...]:
        del selection, time_range
        return ()

    async def store_closed_candles(self, candles: tuple[Candle, ...]) -> None:
        del candles

    async def ping(self) -> bool:
        return True


def build_stub_app() -> object:
    settings = Settings(environment="load-test")
    clock = SystemClock()
    repository = StubRepository()
    historical_provider = StubHistoricalProvider()
    historical = HistoricalMarketDataService(repository, historical_provider, clock)
    datasets = DatasetService(
        repository,
        historical,
        clock,
        lease_duration=timedelta(seconds=120),
        max_dataset_candles=10_000,
    )
    container = Container(
        settings=settings,
        clock=clock,
        repository=repository,
        historical=historical,
        datasets=datasets,
        database=None,
        http_client=None,
        realtime_provider=StubRealtimeProvider(clock),
    )
    return create_app(container)


if __name__ == "__main__":
    uvicorn.run(build_stub_app(), host="127.0.0.1", port=8000, log_level="warning")