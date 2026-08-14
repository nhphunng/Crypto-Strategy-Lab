from __future__ import annotations

import base64
import binascii
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.application.market_data.errors import CandleConflictError, DatasetIntegrityError
from crypto_lab.application.market_data.ports import CandlePage, DatasetClaim
from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.dataset import (
    CandleDataset,
    DatasetStatus,
    dataset_request_key,
    validate_complete_dataset_membership,
)
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.persistence.models import (
    CandleDatasetMemberRow,
    CandleDatasetRow,
    CandleRow,
)


class SqlAlchemyMarketDataRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> tuple[Candle, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(CandleRow)
                    .where(
                        CandleRow.provider == selection.provider,
                        CandleRow.pair == selection.pair,
                        CandleRow.timeframe == selection.timeframe.value,
                        CandleRow.open_time >= time_range.start_time,
                        CandleRow.open_time < time_range.end_time,
                    )
                    .order_by(CandleRow.open_time)
                )
            ).all()
        return tuple(_to_candle(row) for row in rows)

    async def store_closed_candles(self, candles: tuple[Candle, ...]) -> None:
        if not candles:
            return
        for candle in candles:
            if not candle.closed:
                raise ValueError("historical repository accepts only closed Candles")
        now = max(candle.received_at for candle in candles)
        async with self._sessions() as session, session.begin():
            for offset in range(0, len(candles), 1000):
                batch = candles[offset : offset + 1000]
                await session.execute(
                    insert(CandleRow)
                    .values([_candle_values(candle, now) for candle in batch])
                    .on_conflict_do_nothing(
                        index_elements=["provider", "pair", "timeframe", "open_time"]
                    )
                )
            grouped: dict[MarketSelection, list[Candle]] = defaultdict(list)
            for candle in candles:
                grouped[candle.selection].append(candle)
            for selection_key, requested in grouped.items():
                opens = [item.open_time for item in requested]
                stored = (
                    await session.scalars(
                        select(CandleRow).where(
                            CandleRow.provider == selection_key.provider,
                            CandleRow.pair == selection_key.pair,
                            CandleRow.timeframe == selection_key.timeframe.value,
                            CandleRow.open_time.in_(opens),
                        )
                    )
                ).all()
                by_open = {row.open_time: row for row in stored}
                for candle in requested:
                    row = by_open.get(candle.open_time)
                    if row is None or row.content_hash != candle.content_hash:
                        raise CandleConflictError

    async def claim_dataset(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
        now: datetime,
        lease_duration: timedelta,
    ) -> DatasetClaim:
        request_key = dataset_request_key(selection, time_range)
        dataset_id = uuid4()
        build_token = uuid4()
        values = {
            "id": dataset_id,
            "request_key": request_key,
            "schema_version": "1",
            "provider": selection.provider,
            "pair": selection.pair,
            "timeframe": selection.timeframe.value,
            "start_time": time_range.start_time,
            "end_time": time_range.end_time,
            "status": DatasetStatus.BUILDING.value,
            "build_token": build_token,
            "lease_expires_at": now + lease_duration,
            "created_at": now,
            "updated_at": now,
        }
        async with self._sessions() as session, session.begin():
            inserted = await session.scalar(
                insert(CandleDatasetRow)
                .values(values)
                .on_conflict_do_nothing(index_elements=["request_key"])
                .returning(CandleDatasetRow.id)
            )
            if inserted is not None:
                row = await session.get(CandleDatasetRow, inserted)
                assert row is not None
                return DatasetClaim(_to_dataset(row), True, build_token)
            row = await session.scalar(
                select(CandleDatasetRow)
                .where(CandleDatasetRow.request_key == request_key)
                .with_for_update()
            )
            if row is None:
                raise DatasetIntegrityError
            if row.status == DatasetStatus.COMPLETE.value:
                return DatasetClaim(_to_dataset(row), False, None)
            if (
                row.status == DatasetStatus.BUILDING.value
                and row.lease_expires_at is not None
                and row.lease_expires_at > now
            ):
                return DatasetClaim(_to_dataset(row), False, None)
            await session.execute(
                delete(CandleDatasetMemberRow).where(CandleDatasetMemberRow.dataset_id == row.id)
            )
            build_token = uuid4()
            row.status = DatasetStatus.BUILDING.value
            row.build_token = build_token
            row.lease_expires_at = now + lease_duration
            row.candle_count = None
            row.checksum = None
            row.failure_code = None
            row.completed_at = None
            row.updated_at = now
            return DatasetClaim(_to_dataset(row), True, build_token)

    async def finalize_dataset(
        self,
        dataset_id: UUID,
        build_token: UUID,
        candles: tuple[Candle, ...],
        now: datetime,
    ) -> CandleDataset:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(CandleDatasetRow).where(CandleDatasetRow.id == dataset_id).with_for_update()
            )
            if (
                row is None
                or row.status != DatasetStatus.BUILDING.value
                or row.build_token != build_token
            ):
                raise DatasetIntegrityError
            selection = _selection(row)
            time_range = TimeRange(row.start_time, row.end_time)
            expected_checksum = validate_complete_dataset_membership(selection, time_range, candles)
            stored_rows = (
                await session.scalars(
                    select(CandleRow)
                    .where(
                        CandleRow.provider == row.provider,
                        CandleRow.pair == row.pair,
                        CandleRow.timeframe == row.timeframe,
                        CandleRow.open_time >= row.start_time,
                        CandleRow.open_time < row.end_time,
                    )
                    .order_by(CandleRow.open_time)
                )
            ).all()
            stored_candles = tuple(_to_candle(value) for value in stored_rows)
            stored_checksum = validate_complete_dataset_membership(
                selection, time_range, stored_candles
            )
            if stored_checksum != expected_checksum:
                raise DatasetIntegrityError
            member_values = [
                {"dataset_id": dataset_id, "position": index, "candle_id": value.id}
                for index, value in enumerate(stored_rows)
            ]
            for offset in range(0, len(member_values), 5000):
                await session.execute(
                    insert(CandleDatasetMemberRow).values(member_values[offset : offset + 5000])
                )
            row.status = DatasetStatus.COMPLETE.value
            row.candle_count = len(stored_rows)
            row.checksum = stored_checksum
            row.build_token = None
            row.lease_expires_at = None
            row.failure_code = None
            row.updated_at = now
            row.completed_at = now
            return _to_dataset(row)

    async def mark_dataset(
        self,
        dataset_id: UUID,
        build_token: UUID,
        status: DatasetStatus,
        failure_code: str,
        now: datetime,
    ) -> CandleDataset:
        if status not in (DatasetStatus.INCOMPLETE, DatasetStatus.FAILED):
            raise ValueError("only terminal unsuccessful states may be marked")
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(CandleDatasetRow).where(CandleDatasetRow.id == dataset_id).with_for_update()
            )
            if row is None or row.build_token != build_token:
                raise DatasetIntegrityError
            row.status = status.value
            row.build_token = None
            row.lease_expires_at = None
            row.failure_code = failure_code
            row.updated_at = now
            return _to_dataset(row)

    async def get_dataset(self, dataset_id: UUID, *, verify: bool = True) -> CandleDataset | None:
        async with self._sessions() as session:
            row = await session.get(CandleDatasetRow, dataset_id)
            if row is None:
                return None
            dataset = _to_dataset(row)
            if verify and dataset.status is DatasetStatus.COMPLETE:
                candles = await self._dataset_candles(session, dataset_id)
                checksum = validate_complete_dataset_membership(
                    dataset.selection, dataset.time_range, candles
                )
                if checksum != dataset.checksum or len(candles) != dataset.candle_count:
                    raise DatasetIntegrityError
            return dataset

    async def list_dataset_candles(
        self,
        dataset_id: UUID,
        cursor: str | None,
        page_size: int,
    ) -> CandlePage:
        start = _decode_cursor(cursor) + 1 if cursor else 0
        async with self._sessions() as session:
            dataset = await session.get(CandleDatasetRow, dataset_id)
            if dataset is None or dataset.status != DatasetStatus.COMPLETE.value:
                raise DatasetIntegrityError
            rows = (
                await session.execute(
                    select(CandleDatasetMemberRow.position, CandleRow)
                    .join(CandleRow, CandleRow.id == CandleDatasetMemberRow.candle_id)
                    .where(
                        CandleDatasetMemberRow.dataset_id == dataset_id,
                        CandleDatasetMemberRow.position >= start,
                    )
                    .order_by(CandleDatasetMemberRow.position)
                    .limit(page_size + 1)
                )
            ).all()
            has_more = len(rows) > page_size
            visible = rows[:page_size]
            candles = tuple(_to_candle(row.CandleRow) for row in visible)
            next_cursor = _encode_cursor(visible[-1].position) if has_more and visible else None
            return CandlePage(candles, next_cursor, has_more)

    async def ping(self) -> bool:
        try:
            async with self._sessions() as session:
                ready = await session.scalar(
                    text(
                        "SELECT to_regclass('public.candles') IS NOT NULL "
                        "AND to_regclass('public.candle_datasets') IS NOT NULL "
                        "AND to_regclass('public.candle_dataset_members') IS NOT NULL"
                    )
                )
        except Exception:
            return False
        return bool(ready)

    @staticmethod
    async def _dataset_candles(session: AsyncSession, dataset_id: UUID) -> tuple[Candle, ...]:
        rows = (
            await session.scalars(
                select(CandleRow)
                .join(
                    CandleDatasetMemberRow,
                    CandleDatasetMemberRow.candle_id == CandleRow.id,
                )
                .where(CandleDatasetMemberRow.dataset_id == dataset_id)
                .order_by(CandleDatasetMemberRow.position)
            )
        ).all()
        return tuple(_to_candle(row) for row in rows)


def _candle_values(candle: Candle, created_at: datetime) -> dict[str, object]:
    return {
        "id": uuid4(),
        "provider": candle.provider,
        "pair": candle.pair,
        "timeframe": candle.timeframe.value,
        "open_time": candle.open_time,
        "close_time": candle.close_time,
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
        "volume": candle.volume,
        "closed": candle.closed,
        "received_at": candle.received_at,
        "content_hash": candle.content_hash,
        "created_at": created_at,
    }


def _to_candle(row: CandleRow) -> Candle:
    return Candle(
        provider=row.provider,
        pair=row.pair,
        timeframe=Timeframe(row.timeframe),
        open_time=row.open_time,
        close_time=row.close_time,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        closed=row.closed,
        received_at=row.received_at,
    )


def _selection(row: CandleDatasetRow) -> MarketSelection:
    return MarketSelection(row.provider, row.pair, Timeframe(row.timeframe))


def _to_dataset(row: CandleDatasetRow) -> CandleDataset:
    return CandleDataset(
        id=row.id,
        schema_version=row.schema_version,
        selection=_selection(row),
        time_range=TimeRange(row.start_time, row.end_time),
        status=DatasetStatus(row.status),
        candle_count=row.candle_count,
        checksum=row.checksum,
        failure_code=row.failure_code,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def _encode_cursor(position: int) -> str:
    return base64.urlsafe_b64encode(str(position).encode("ascii")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> int:
    if len(cursor) > 128:
        raise ValueError("invalid cursor")
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("ascii")
        position = int(decoded)
    except (ValueError, UnicodeError, binascii.Error) as error:
        raise ValueError("invalid cursor") from error
    if position < 0:
        raise ValueError("invalid cursor")
    return position
