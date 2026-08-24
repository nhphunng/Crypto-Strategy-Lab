from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from crypto_lab.application.market_data.errors import CandleConflictError, DatasetIntegrityError
from crypto_lab.application.market_data.ports import CandlePage, DatasetClaim
from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.dataset import (
    CandleDataset,
    DatasetStatus,
    calculate_dataset_checksum,
    dataset_request_key,
    validate_complete_dataset_membership,
)
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe


class FixedClock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


class MutableClock:
    """Test clock whose reported instant can be advanced between phases."""

    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value

    def advance(self, value: datetime) -> None:
        if value < self.value:
            raise ValueError("mutable clock cannot move backward")
        self.value = value


def make_candle(
    open_time: datetime,
    *,
    selection: MarketSelection | None = None,
    open: str = "100",
    high: str = "102",
    low: str = "99",
    close: str = "101.25",
    closed: bool = True,
    received_at: datetime | None = None,
) -> Candle:
    selection = selection or MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
    return Candle(
        provider=selection.provider,
        pair=selection.pair,
        timeframe=selection.timeframe,
        open_time=open_time,
        close_time=selection.timeframe.close_time(open_time),
        open=Decimal(open),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("12.5"),
        closed=closed,
        received_at=received_at or datetime(2026, 8, 13, 12, tzinfo=UTC),
    )


class FakeProvider:
    provider = "BINANCE"

    def __init__(self, candles: tuple[Candle, ...]) -> None:
        self.candles = candles
        self.calls: list[TimeRange] = []

    async def iter_historical(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> AsyncIterator[tuple[Candle, ...]]:
        self.calls.append(time_range)
        page = tuple(
            candle
            for candle in sorted(self.candles, key=lambda item: item.open_time)
            if candle.selection == selection and time_range.contains_open(candle.open_time)
        )
        for offset in range(0, len(page), 1000):
            yield page[offset : offset + 1000]


class InMemoryMarketDataRepository:
    def __init__(self) -> None:
        self.candles: dict[tuple[str, str, str, datetime], Candle] = {}
        self.datasets: dict[UUID, CandleDataset] = {}
        self.dataset_keys: dict[str, UUID] = {}
        self.members: dict[UUID, tuple[Candle, ...]] = {}
        self.tokens: dict[UUID, tuple[UUID, datetime]] = {}

    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> tuple[Candle, ...]:
        return tuple(
            sorted(
                (
                    candle
                    for candle in self.candles.values()
                    if candle.selection == selection and time_range.contains_open(candle.open_time)
                ),
                key=lambda candle: candle.open_time,
            )
        )

    async def store_closed_candles(self, candles: tuple[Candle, ...]) -> None:
        for candle in candles:
            if not candle.closed:
                raise ValueError("historical repository accepts only closed Candles")
            existing = self.candles.get(candle.identity)
            if existing is not None and existing.content_hash != candle.content_hash:
                raise CandleConflictError
            self.candles[candle.identity] = existing or candle

    async def claim_dataset(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
        now: datetime,
        lease_duration: timedelta,
    ) -> DatasetClaim:
        key = dataset_request_key(selection, time_range)
        existing_id = self.dataset_keys.get(key)
        if existing_id is not None:
            dataset = self.datasets[existing_id]
            token_lease = self.tokens.get(existing_id)
            if dataset.status is DatasetStatus.COMPLETE:
                return DatasetClaim(dataset, False, None)
            if token_lease is not None and token_lease[1] > now:
                return DatasetClaim(dataset, False, None)
            dataset_id = existing_id
        else:
            dataset_id = uuid4()
            self.dataset_keys[key] = dataset_id
        token = uuid4()
        self.tokens[dataset_id] = (token, now + lease_duration)
        dataset = CandleDataset(
            id=dataset_id,
            schema_version="1",
            selection=selection,
            time_range=time_range,
            status=DatasetStatus.BUILDING,
            candle_count=None,
            checksum=None,
            failure_code=None,
            created_at=self.datasets.get(
                dataset_id, _stub_dataset(dataset_id, selection, time_range, now)
            ).created_at,
            updated_at=now,
            completed_at=None,
        )
        self.datasets[dataset_id] = dataset
        return DatasetClaim(dataset, True, token)

    async def finalize_dataset(
        self,
        dataset_id: UUID,
        build_token: UUID,
        candles: tuple[Candle, ...],
        now: datetime,
    ) -> CandleDataset:
        dataset = self.datasets[dataset_id]
        if self.tokens.get(dataset_id, (None, None))[0] != build_token:
            raise DatasetIntegrityError
        checksum = validate_complete_dataset_membership(
            dataset.selection, dataset.time_range, candles
        )
        completed = CandleDataset(
            id=dataset.id,
            schema_version="1",
            selection=dataset.selection,
            time_range=dataset.time_range,
            status=DatasetStatus.COMPLETE,
            candle_count=len(candles),
            checksum=checksum,
            failure_code=None,
            created_at=dataset.created_at,
            updated_at=now,
            completed_at=now,
        )
        self.datasets[dataset_id] = completed
        self.members[dataset_id] = candles
        self.tokens.pop(dataset_id, None)
        return completed

    async def mark_dataset(
        self,
        dataset_id: UUID,
        build_token: UUID,
        status: DatasetStatus,
        failure_code: str,
        now: datetime,
    ) -> CandleDataset:
        dataset = self.datasets[dataset_id]
        if self.tokens.get(dataset_id, (None, None))[0] != build_token:
            raise DatasetIntegrityError
        changed = CandleDataset(
            id=dataset.id,
            schema_version="1",
            selection=dataset.selection,
            time_range=dataset.time_range,
            status=status,
            candle_count=None,
            checksum=None,
            failure_code=failure_code,
            created_at=dataset.created_at,
            updated_at=now,
            completed_at=None,
        )
        self.datasets[dataset_id] = changed
        self.tokens.pop(dataset_id, None)
        return changed

    async def get_dataset(self, dataset_id: UUID, *, verify: bool = True) -> CandleDataset | None:
        dataset = self.datasets.get(dataset_id)
        if dataset and verify and dataset.status is DatasetStatus.COMPLETE:
            if calculate_dataset_checksum(self.members[dataset_id]) != dataset.checksum:
                raise DatasetIntegrityError
        return dataset

    async def list_dataset_candles(
        self,
        dataset_id: UUID,
        cursor: str | None,
        page_size: int,
    ) -> CandlePage:
        await self.get_dataset(dataset_id, verify=True)
        start = int(cursor) + 1 if cursor is not None else 0
        page = self.members.get(dataset_id, ())[start : start + page_size]
        end_position = start + len(page) - 1
        has_more = start + len(page) < len(self.members.get(dataset_id, ()))
        return CandlePage(page, str(end_position) if has_more else None, has_more)

    async def ping(self) -> bool:
        return True


def _stub_dataset(
    dataset_id: UUID,
    selection: MarketSelection,
    time_range: TimeRange,
    now: datetime,
) -> CandleDataset:
    return CandleDataset(
        id=dataset_id,
        schema_version="1",
        selection=selection,
        time_range=time_range,
        status=DatasetStatus.BUILDING,
        candle_count=None,
        checksum=None,
        failure_code=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
