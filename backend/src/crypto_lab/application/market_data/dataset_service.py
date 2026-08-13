from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from crypto_lab.application.market_data.errors import MarketDataError, invalid_request
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.market_data.ports import CandlePage, Clock, MarketDataRepository
from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import CandleDataset, DatasetStatus
from crypto_lab.domain.market_data.ranges import Completeness, TimeRange


@dataclass(frozen=True, slots=True)
class MaterializationResult:
    dataset: CandleDataset
    created: bool
    building: bool = False


class DatasetService:
    def __init__(
        self,
        repository: MarketDataRepository,
        historical_service: HistoricalMarketDataService,
        clock: Clock,
        *,
        lease_duration: timedelta,
        max_dataset_candles: int,
    ) -> None:
        self._repository = repository
        self._historical = historical_service
        self._clock = clock
        self._lease_duration = lease_duration
        self._max_dataset_candles = max_dataset_candles

    async def materialize(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
        *,
        request_id: str | None = None,
    ) -> MaterializationResult:
        self._historical.validate_request(selection, time_range, self._max_dataset_candles)
        expected_count = time_range.expected_count(selection.timeframe)
        if expected_count > self._max_dataset_candles:
            raise invalid_request(
                "MARKET_RANGE_TOO_LARGE",
                "The requested dataset exceeds the configured Candle limit.",
                limit=self._max_dataset_candles,
            )
        now = self._clock.now()
        claim = await self._repository.claim_dataset(
            selection, time_range, now, self._lease_duration
        )
        if not claim.acquired:
            return MaterializationResult(
                claim.dataset,
                created=False,
                building=claim.dataset.status is DatasetStatus.BUILDING,
            )
        if claim.build_token is None:
            raise RuntimeError("acquired dataset claim requires build token")
        try:
            history = await self._historical.get_range(
                selection,
                time_range,
                limit=self._max_dataset_candles,
                request_id=request_id,
            )
            if history.completeness is not Completeness.COMPLETE:
                dataset = await self._repository.mark_dataset(
                    claim.dataset.id,
                    claim.build_token,
                    DatasetStatus.INCOMPLETE,
                    "MARKET_DATASET_INCOMPLETE",
                    self._clock.now(),
                )
                return MaterializationResult(dataset, created=True)
            dataset = await self._repository.finalize_dataset(
                claim.dataset.id,
                claim.build_token,
                history.candles,
                self._clock.now(),
            )
            return MaterializationResult(dataset, created=True)
        except MarketDataError as error:
            await self._repository.mark_dataset(
                claim.dataset.id,
                claim.build_token,
                DatasetStatus.FAILED,
                error.descriptor.code,
                self._clock.now(),
            )
            raise
        except Exception:
            await self._repository.mark_dataset(
                claim.dataset.id,
                claim.build_token,
                DatasetStatus.FAILED,
                "MARKET_INTERNAL_ERROR",
                self._clock.now(),
            )
            raise

    async def get(self, dataset_id: UUID) -> CandleDataset:
        dataset = await self._repository.get_dataset(dataset_id, verify=True)
        if dataset is None:
            raise invalid_request("MARKET_DATASET_NOT_FOUND", "The dataset was not found.")
        return dataset

    async def list_candles(
        self,
        dataset_id: UUID,
        cursor: str | None,
        page_size: int,
    ) -> CandlePage:
        if page_size < 1 or page_size > 1000:
            raise invalid_request(
                "MARKET_REQUEST_MALFORMED", "pageSize must be between 1 and 1000."
            )
        dataset = await self.get(dataset_id)
        if dataset.status is not DatasetStatus.COMPLETE:
            raise invalid_request(
                "MARKET_DATASET_INCOMPLETE",
                "Only a complete dataset exposes reusable Candle membership.",
            )
        return await self._repository.list_dataset_candles(dataset_id, cursor, page_size)
