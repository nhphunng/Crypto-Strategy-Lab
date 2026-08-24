from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from crypto_lab.api.leaderboard_dependencies import (
    LeaderboardContainer,
    build_leaderboard_container,
)
from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.market_data.ports import (
    Clock,
    MarketDataRepository,
    RealtimeMarketDataProvider,
)
from crypto_lab.infrastructure.binance.market_data_provider import BinanceMarketDataProvider
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.market_data.binance_realtime_provider import (
    BinanceRealtimeMarketProvider,
)
from crypto_lab.infrastructure.market_data.realtime_selection_hub import (
    RealtimeSelectionHub,
)
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
    realtime_provider: RealtimeMarketDataProvider | None = None
    realtime_hub: RealtimeSelectionHub | None = None
    leaderboard: LeaderboardContainer | None = None

    async def close(self) -> None:
        if self.realtime_hub is not None:
            await self.realtime_hub.close()
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
    realtime_provider = BinanceRealtimeMarketProvider(
        clock,
        websocket_url=settings.binance_websocket_url,
        heartbeat_interval_seconds=settings.provider_heartbeat_interval_seconds,
        stale_after_seconds=settings.provider_stale_after_seconds,
    )
    realtime_hub = RealtimeSelectionHub(realtime_provider)
    return Container(
        settings=settings,
        clock=clock,
        repository=repository,
        historical=historical,
        datasets=datasets,
        database=database,
        http_client=client,
        realtime_provider=realtime_provider,
        realtime_hub=realtime_hub,
        leaderboard=build_leaderboard_container(database),
    )
