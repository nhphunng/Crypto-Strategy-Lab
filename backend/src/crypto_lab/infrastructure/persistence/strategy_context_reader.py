from __future__ import annotations

from uuid import UUID

from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.strategy.context import ContextCompleteness, StrategyContext
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)


class SqlAlchemyStrategyContextReader:
    def __init__(self, repository: SqlAlchemyMarketDataRepository) -> None:
        self._repository = repository

    async def get_strategy_context(self, dataset_id: str) -> StrategyContext | None:
        try:
            identity = UUID(dataset_id)
        except ValueError:
            return None
        dataset = await self._repository.get_dataset(identity)
        if dataset is None or dataset.status is not DatasetStatus.COMPLETE:
            return None
        page = await self._repository.list_dataset_candles(
            identity, None, dataset.candle_count or 1
        )
        return StrategyContext(
            dataset_id=str(dataset.id),
            dataset_version=dataset.checksum or "",
            provider=dataset.selection.provider,
            pair=dataset.selection.pair,
            timeframe=dataset.selection.timeframe,
            range_start=dataset.time_range.start_time,
            range_end=dataset.time_range.end_time,
            decision_timestamp=dataset.time_range.end_time,
            completeness=ContextCompleteness.COMPLETE,
            candles=page.candles,
        )
