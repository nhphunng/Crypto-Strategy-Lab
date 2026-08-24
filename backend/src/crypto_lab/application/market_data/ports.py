from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.dataset import CandleDataset, DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.domain.market_data.timeframe import require_utc


class Clock(Protocol):
    def now(self) -> datetime: ...


class HistoricalMarketDataProvider(Protocol):
    provider: str

    def iter_historical(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> AsyncIterator[tuple[Candle, ...]]: ...


class MarketDataProvider(HistoricalMarketDataProvider, Protocol):
    """Backward-compatible name for the Feature 001 historical provider port."""


class RealtimeProviderEventType(StrEnum):
    CANDLE = "CANDLE"
    HEARTBEAT = "HEARTBEAT"
    DISCONNECTED = "DISCONNECTED"


@dataclass(frozen=True, slots=True)
class RealtimeProviderEvent:
    event_type: RealtimeProviderEventType
    selection: MarketSelection
    occurred_at: datetime
    candle: Candle | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "occurred_at", require_utc(self.occurred_at))
        if self.event_type is RealtimeProviderEventType.CANDLE:
            if self.candle is None or self.candle.selection != self.selection:
                raise ValueError("CANDLE event must contain a matching Candle")
        elif self.candle is not None:
            raise ValueError("Only CANDLE events may contain a Candle")
        if self.reason_code is not None and (
            not self.reason_code or self.reason_code != self.reason_code.upper()
        ):
            raise ValueError("reason_code must be uppercase")


class RealtimeMarketDataProvider(Protocol):
    provider: str

    def stream(
        self,
        selection: MarketSelection,
    ) -> AsyncGenerator[RealtimeProviderEvent, None]: ...

    async def release(self, selection: MarketSelection) -> None: ...

    def last_closed_checkpoint(self, selection: MarketSelection) -> datetime | None:
        """Report the open time of the last closed Candle observed for a selection.

        The continuity checkpoint supports gap recovery and observability; a selection
        with no observed closed Candle reports ``None``.
        """
        ...


@dataclass(frozen=True, slots=True)
class DatasetClaim:
    dataset: CandleDataset
    acquired: bool
    build_token: UUID | None


@dataclass(frozen=True, slots=True)
class CandlePage:
    candles: tuple[Candle, ...]
    next_cursor: str | None
    has_more: bool


class HistoricalCandleRepository(Protocol):
    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> tuple[Candle, ...]: ...

    async def store_closed_candles(self, candles: tuple[Candle, ...]) -> None: ...

    async def ping(self) -> bool: ...


class MarketDataRepository(HistoricalCandleRepository, Protocol):
    async def claim_dataset(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
        now: datetime,
        lease_duration: timedelta,
    ) -> DatasetClaim: ...

    async def finalize_dataset(
        self,
        dataset_id: UUID,
        build_token: UUID,
        candles: tuple[Candle, ...],
        now: datetime,
    ) -> CandleDataset: ...

    async def mark_dataset(
        self,
        dataset_id: UUID,
        build_token: UUID,
        status: DatasetStatus,
        failure_code: str,
        now: datetime,
    ) -> CandleDataset: ...

    async def get_dataset(
        self, dataset_id: UUID, *, verify: bool = True
    ) -> CandleDataset | None: ...

    async def list_dataset_candles(
        self,
        dataset_id: UUID,
        cursor: str | None,
        page_size: int,
    ) -> CandlePage: ...
