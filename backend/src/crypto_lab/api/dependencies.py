from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.market_data.ports import Clock, MarketDataRepository
from crypto_lab.infrastructure.binance.market_data_provider import BinanceMarketDataProvider
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from crypto_lab.infrastructure.settings import Settings


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(slots=True)
class Container:
    settings: Settings
    clock: Clock
    repository: MarketDataRepository
    historical: HistoricalMarketDataService
    datasets: DatasetService
    database: Database | None = None
    http_client: httpx.AsyncClient | None = None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()
        if self.database is not None:
            await self.database.dispose()


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or Settings()
    clock = SystemClock()
    database = Database.create(settings.database_url)
    repository = SqlAlchemyMarketDataRepository(database.sessions)
    timeout = httpx.Timeout(
        connect=settings.provider_connect_timeout_seconds,
        read=settings.provider_read_timeout_seconds,
        write=settings.provider_read_timeout_seconds,
        pool=settings.provider_connect_timeout_seconds,
    )
    client = httpx.AsyncClient(timeout=timeout)
    provider = BinanceMarketDataProvider(
        client,
        clock,
        base_url=settings.binance_base_url,
        max_attempts=settings.provider_max_attempts,
        max_retry_delay_seconds=settings.provider_max_retry_delay_seconds,
    )
    historical = HistoricalMarketDataService(repository, provider, clock)
    datasets = DatasetService(
        repository,
        historical,
        clock,
        lease_duration=timedelta(seconds=settings.dataset_build_lease_seconds),
        max_dataset_candles=settings.max_dataset_candles,
    )
    return Container(
        settings,
        clock,
        repository,
        historical,
        datasets,
        database,
        client,
    )
