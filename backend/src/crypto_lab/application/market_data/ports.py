from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.dataset import CandleDataset, DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange


class Clock(Protocol):
    def now(self) -> datetime: ...


class MarketDataProvider(Protocol):
    provider: str

    def iter_historical(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> AsyncIterator[tuple[Candle, ...]]: ...


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


class MarketDataRepository(Protocol):
    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> tuple[Candle, ...]: ...

    async def store_closed_candles(self, candles: tuple[Candle, ...]) -> None: ...

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

    async def ping(self) -> bool: ...
