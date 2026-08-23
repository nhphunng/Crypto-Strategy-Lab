from __future__ import annotations

from typing import Protocol

from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.ranges import HistoricalCandleRange, TimeRange
from crypto_lab.domain.market_data.selection import MarketSelection


class HistoricalCandleReader(Protocol):
    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> tuple[Candle, ...]: ...


class HistoricalRangeUseCase(Protocol):
    async def get_range(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
        *,
        limit: int,
        request_id: str | None = None,
    ) -> HistoricalCandleRange: ...


class HistoricalGapBackfillAdapter:
    """Expose the accepted TV1 acquisition use case as a recovery reader."""

    def __init__(self, historical: HistoricalRangeUseCase, *, limit: int) -> None:
        if limit < 1 or limit > 1_000:
            raise ValueError("limit must be between one and 1,000")
        self._historical = historical
        self._limit = limit

    async def read_candles(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> tuple[Candle, ...]:
        result = await self._historical.get_range(
            selection,
            time_range,
            limit=self._limit,
        )
        return result.candles
