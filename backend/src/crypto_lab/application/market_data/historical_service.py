from __future__ import annotations

import logging
from time import perf_counter

from crypto_lab.application.market_data.errors import ProviderPayloadInvalid, invalid_request
from crypto_lab.application.market_data.ports import Clock, MarketDataProvider, MarketDataRepository
from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.ranges import (
    HistoricalCandleRange,
    TimeRange,
    derive_historical_range,
)
from crypto_lab.domain.market_data.timeframe import Timeframe

logger = logging.getLogger(__name__)


class HistoricalMarketDataService:
    def __init__(
        self,
        repository: MarketDataRepository,
        provider: MarketDataProvider,
        clock: Clock,
        *,
        supported_pairs: frozenset[str] = frozenset({"BTCUSDT"}),
        supported_timeframes: frozenset[Timeframe] = frozenset(Timeframe),
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._clock = clock
        self._supported_pairs = supported_pairs
        self._supported_timeframes = supported_timeframes

    async def get_range(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
        *,
        limit: int,
        request_id: str | None = None,
    ) -> HistoricalCandleRange:
        started = perf_counter()
        self.validate_request(selection, time_range, limit)
        local = await self._repository.read_candles(selection, time_range)
        initial = derive_historical_range(selection, time_range, local)
        fetched_count = 0
        for missing_range in initial.missing_ranges:
            async for page in self._provider.iter_historical(selection, missing_range):
                self._validate_page(selection, missing_range, page)
                await self._repository.store_closed_candles(page)
                fetched_count += len(page)
        canonical = await self._repository.read_candles(selection, time_range)
        result = derive_historical_range(selection, time_range, canonical)
        logger.info(
            "historical_range_resolved",
            extra={
                "fields": {
                    "request_id": request_id,
                    "provider": selection.provider,
                    "pair": selection.pair,
                    "timeframe": selection.timeframe.value,
                    "local_count": len(local),
                    "fetched_count": fetched_count,
                    "completeness": result.completeness.value,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                }
            },
        )
        return result

    def validate_request(
        self, selection: MarketSelection, time_range: TimeRange, limit: int
    ) -> None:
        if selection.provider != self._provider.provider:
            raise invalid_request(
                "MARKET_PROVIDER_UNSUPPORTED", "The requested provider is not supported."
            )
        if selection.pair not in self._supported_pairs:
            raise invalid_request("MARKET_PAIR_UNSUPPORTED", "The requested pair is not supported.")
        if selection.timeframe not in self._supported_timeframes:
            raise invalid_request(
                "MARKET_TIMEFRAME_UNSUPPORTED", "The requested timeframe is not supported."
            )
        try:
            time_range.validate_alignment(selection.timeframe)
        except ValueError as error:
            raise invalid_request(
                "MARKET_RANGE_UNALIGNED",
                "Range boundaries must align to the selected timeframe.",
            ) from error
        if limit < 1 or time_range.expected_count(selection.timeframe) > limit:
            raise invalid_request(
                "MARKET_RANGE_TOO_LARGE",
                "The requested range exceeds the allowed Candle count.",
                limit=limit,
            )
        latest_closed_boundary = selection.timeframe.floor(self._clock.now())
        if time_range.end_time > latest_closed_boundary:
            raise invalid_request(
                "MARKET_RANGE_NOT_CLOSED",
                "The requested range includes an interval that is not known to be closed.",
            )

    @staticmethod
    def _validate_page(
        selection: MarketSelection,
        time_range: TimeRange,
        page: tuple[Candle, ...],
    ) -> None:
        if not page or len(page) > 1000:
            raise ProviderPayloadInvalid
        for value in page:
            if value.selection != selection or not time_range.contains_open(value.open_time):
                raise ProviderPayloadInvalid
            if not value.closed:
                raise ProviderPayloadInvalid
