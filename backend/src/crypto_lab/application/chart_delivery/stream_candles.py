from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from crypto_lab.application.chart_delivery.historical_backfill import HistoricalCandleReader
from crypto_lab.application.market_data.candle_merge import (
    CandleUpdate,
    ClosedCandleConflictError,
    merge_live_candle,
)
from crypto_lab.application.market_data.ports import (
    Clock,
    RealtimeMarketDataProvider,
    RealtimeProviderEvent,
    RealtimeProviderEventType,
)
from crypto_lab.application.market_data.recover_stream import (
    RecoveryController,
    RecoveryPolicy,
    RecoveryState,
    merge_recovery_batch,
    recovery_backfill_range,
)
from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.ranges import Completeness, derive_historical_range
from crypto_lab.domain.market_data.selection import ConnectionState, MarketSelection


class DeliveryEventType(StrEnum):
    CANDLE = "CANDLE"
    STATE = "STATE"


@dataclass(frozen=True, slots=True)
class CandleDelivery:
    event_type: DeliveryEventType
    selection: MarketSelection
    occurred_at: datetime
    candle: Candle | None = None
    revision: int | None = None
    state: ConnectionState | None = None
    attempt: int = 0
    reason_code: str | None = None
    retry_after_ms: int = 0
    last_event_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.event_type is DeliveryEventType.CANDLE:
            if self.candle is None or self.revision is None or self.state is not None:
                raise ValueError("CANDLE delivery requires Candle and revision only")
        elif self.state is None or self.candle is not None or self.revision is not None:
            raise ValueError("STATE delivery requires connection state only")


class StreamCandles:
    """Normalize one provider stream into deduplicated, revisioned deliveries.

    When a historical repository and recovery policy are provided, a disconnected
    stream is recovered with capped backoff. Before LIVE is re-announced, the closed
    interval gap after the last accepted closed candle is backfilled so the consumer
    never receives a gap as if it were live data.
    """

    def __init__(
        self,
        provider: RealtimeMarketDataProvider,
        clock: Clock,
        *,
        max_candles: int = 1_000,
        history: HistoricalCandleReader | None = None,
        recovery_policy: RecoveryPolicy | None = None,
        connectivity: Callable[[], bool] = lambda: True,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if max_candles < 1 or max_candles > 1_000:
            raise ValueError("max_candles must be between one and 1,000")
        self._provider = provider
        self._clock = clock
        self._max_candles = max_candles
        self._history = history
        self._recovery_policy = recovery_policy
        self._connectivity = connectivity
        self._sleep = sleep

    async def stream(self, selection: MarketSelection) -> AsyncIterator[CandleDelivery]:
        series: tuple[CandleUpdate, ...] = ()
        checkpoint: datetime | None = None
        last_event_at: datetime | None = None
        live_announced = False
        controller = RecoveryController(
            self._recovery_policy,
            connectivity=self._connectivity,
        )

        while True:
            stream = self._provider.stream(selection)
            disconnect: RealtimeProviderEvent | None = None
            reason_code: str | None = None
            try:
                async for event in stream:
                    if event.event_type is RealtimeProviderEventType.DISCONNECTED:
                        disconnect = event
                        break
                    if (
                        not live_announced
                        and checkpoint is not None
                        and event.event_type is not RealtimeProviderEventType.HEARTBEAT
                    ):
                        reached = await self._reach_live(selection, series, checkpoint, event)
                        if reached is None:
                            disconnect = event
                            reason_code = "MARKET_GAP_RECOVERY_FAILED"
                            break
                        series, checkpoint, recovered = reached
                        live_announced = True
                        for update in recovered:
                            last_event_at = update.candle.received_at
                            yield CandleDelivery(
                                DeliveryEventType.CANDLE,
                                selection,
                                event.occurred_at,
                                candle=update.candle,
                                revision=update.revision,
                            )
                        yield self._state(
                            selection,
                            ConnectionState.LIVE,
                            occurred_at=event.occurred_at,
                            attempt=controller.attempt,
                        )
                    if event.event_type is RealtimeProviderEventType.HEARTBEAT:
                        if not live_announced:
                            live_announced = True
                            yield self._state(
                                selection,
                                ConnectionState.LIVE,
                                occurred_at=event.occurred_at,
                                attempt=controller.attempt,
                            )
                        continue
                    candle = event.candle
                    if candle is None:
                        continue
                    try:
                        merged = merge_live_candle(series, candle, limit=self._max_candles)
                    except ClosedCandleConflictError:
                        # A conflicting terminal update is quarantined from the public series.
                        continue
                    if merged == series:
                        continue
                    series = merged
                    update = series[-1]
                    last_event_at = update.candle.received_at
                    if update.candle.closed:
                        checkpoint = update.candle.open_time
                    yield CandleDelivery(
                        DeliveryEventType.CANDLE,
                        selection,
                        event.occurred_at,
                        candle=update.candle,
                        revision=update.revision,
                    )
                    if not live_announced:
                        live_announced = True
                        yield self._state(
                            selection,
                            ConnectionState.LIVE,
                            occurred_at=event.occurred_at,
                            attempt=controller.attempt,
                        )
            finally:
                await stream.aclose()

            if disconnect is None:
                return

            signal = controller.on_disconnect(reason_code=reason_code or disconnect.reason_code)
            yield self._state(
                selection,
                ConnectionState.STALE,
                occurred_at=disconnect.occurred_at,
                attempt=signal.attempt,
                reason_code=signal.reason_code,
                last_event_at=last_event_at,
            )
            live_announced = False

            while True:
                signal = controller.begin_reconnect()
                if signal.state is RecoveryState.ERROR:
                    yield self._state(
                        selection,
                        ConnectionState.ERROR,
                        attempt=signal.attempt,
                        reason_code=signal.reason_code,
                        last_event_at=last_event_at,
                    )
                    return
                if signal.state is RecoveryState.PAUSED_OFFLINE:
                    yield self._state(
                        selection,
                        ConnectionState.RECONNECTING,
                        attempt=signal.attempt,
                        last_event_at=last_event_at,
                    )
                    await self._wait_for_online()
                    continue
                yield self._state(
                    selection,
                    ConnectionState.RECONNECTING,
                    attempt=signal.attempt,
                    retry_after_ms=signal.retry_after_ms,
                    last_event_at=last_event_at,
                )
                await self._sleep(signal.retry_after_ms / 1000)
                break

    async def release(self, selection: MarketSelection) -> None:
        await self._provider.release(selection)

    async def _reach_live(
        self,
        selection: MarketSelection,
        series: tuple[CandleUpdate, ...],
        checkpoint: datetime,
        event: RealtimeProviderEvent,
    ) -> tuple[tuple[CandleUpdate, ...], datetime | None, tuple[CandleUpdate, ...]] | None:
        """Close the historical gap before LIVE so recovery never resumes with stale data.

        Returns the updated series, the refreshed checkpoint, and the recovered closed
        candles, or None when the gap cannot be backfilled completely.
        """
        backfill = recovery_backfill_range(checkpoint, selection.timeframe, event.occurred_at)
        if backfill is None or self._history is None:
            return series, checkpoint, ()
        candles = await self._history.read_candles(selection, backfill)
        derived = derive_historical_range(selection, backfill, candles)
        if derived.completeness is not Completeness.COMPLETE:
            return None
        truncated = tuple(update for update in series if update.candle.open_time <= checkpoint)
        merged = merge_recovery_batch(truncated, derived.candles, limit=self._max_candles)
        if not merged:
            return series, checkpoint, ()
        new_checkpoint = merged[-1].candle.open_time
        before = {update.candle.content_hash for update in truncated}
        recovered = tuple(update for update in merged if update.candle.content_hash not in before)
        return merged, new_checkpoint, recovered

    async def _wait_for_online(self) -> None:
        while not self._connectivity():
            await self._sleep(1.0)

    def _state(
        self,
        selection: MarketSelection,
        state: ConnectionState,
        *,
        occurred_at: datetime | None = None,
        attempt: int = 0,
        reason_code: str | None = None,
        retry_after_ms: int = 0,
        last_event_at: datetime | None = None,
    ) -> CandleDelivery:
        return CandleDelivery(
            DeliveryEventType.STATE,
            selection,
            occurred_at or self._clock.now(),
            state=state,
            attempt=attempt,
            reason_code=reason_code,
            retry_after_ms=retry_after_ms,
            last_event_at=last_event_at,
        )
