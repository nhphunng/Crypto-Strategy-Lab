from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.market_data.ports import (
    Clock,
    MarketDataRepository,
    RealtimeMarketDataProvider,
)
from crypto_lab.application.strategies.activate_generated_strategy import ActivateGeneratedStrategy
from crypto_lab.application.strategies.analyze_strategy import AnalyzeStrategy
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.application.strategies.generate_strategies import GenerateStrategies
from crypto_lab.application.strategies.ports import (
    GeneratedArtifactStore,
    StrategyDefinitionRepository,
    StrategyGenerationRepository,
)
from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.strategy.errors import StrategyError
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.binance.market_data_provider import BinanceMarketDataProvider
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.llm.strategy_generation_adapter import (
    StructuredStrategyGenerationAdapter,
)
from crypto_lab.infrastructure.market_data.binance_realtime_provider import (
    BinanceRealtimeMarketProvider,
)
from crypto_lab.infrastructure.market_data.realtime_selection_hub import (
    RealtimeSelectionHub,
)
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from crypto_lab.infrastructure.persistence.repositories.strategy_definition_repository import (
    SqlAlchemyStrategyDefinitionRepository,
)
from crypto_lab.infrastructure.persistence.repositories.strategy_generation_repository import (
    SqlAlchemyStrategyGenerationRepository,
)
from crypto_lab.infrastructure.persistence.strategy_context_reader import (
    SqlAlchemyStrategyContextReader,
)
from crypto_lab.infrastructure.sandbox.encrypted_artifact_store import (
    EncryptedFilesystemArtifactStore,
)
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)
from crypto_lab.infrastructure.sandbox.isolated_generated_strategy import (
    IsolatedGeneratedStrategy,
)
from crypto_lab.infrastructure.security.source_content_protector import (
    LocalAesKeyProvider,
    SourceContentProtector,
)
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.infrastructure.sources.web_source_adapter import SafeWebSourceAdapter


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
    strategy_registry: StrategyRegistry | None = None
    strategy_discovery: DiscoverStrategies | None = None
    strategy_analysis: AnalyzeStrategy | None = None
    strategy_generation_repository: StrategyGenerationRepository | None = None
    strategy_generation: GenerateStrategies | None = None
    strategy_activation: ActivateGeneratedStrategy | None = None
    generated_artifacts: GeneratedArtifactStore | None = None
    generated_runtime: DockerGeneratedStrategyRuntime | None = None
    strategy_definitions: StrategyDefinitionRepository | None = None
    realtime_provider: RealtimeMarketDataProvider | None = None
    realtime_hub: RealtimeSelectionHub | None = None

    async def load_generated_strategies(self) -> None:
        if (
            self.strategy_generation_repository is None
            or self.generated_artifacts is None
            or self.generated_runtime is None
            or self.strategy_registry is None
        ):
            return
        for provenance in await self.strategy_generation_repository.list_activated():
            version = SemanticVersion.parse(provenance.strategy_version)
            try:
                self.strategy_registry.metadata(provenance.strategy_id, version)
            except StrategyError:
                pass
            else:
                continue
            draft = await self.strategy_generation_repository.get_draft(provenance.draft_id)
            metadata = await self.strategy_generation_repository.get_artifact(
                provenance.artifact_id
            )
            if draft is None or metadata is None:
                continue
            artifact = await self.generated_artifacts.get(metadata.content_fingerprint)
            self.strategy_registry.register(
                IsolatedGeneratedStrategy(
                    strategy_id=provenance.strategy_id,
                    display_name=draft.display_name,
                    strategy_version=version,
                    parameter_schema=draft.parameter_schema,
                    artifact=artifact,
                    runtime=self.generated_runtime,
                    generation_provenance_id=provenance.id,
                )
            )

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
    strategy_registry = build_strategy_registry()
    strategy_discovery = DiscoverStrategies(strategy_registry)
    strategy_definitions = SqlAlchemyStrategyDefinitionRepository(database.sessions)
    strategy_contexts = SqlAlchemyStrategyContextReader(repository)
    strategy_analysis = AnalyzeStrategy(
        strategy_definitions,
        strategy_contexts,
        strategy_registry,
    )
    generation_repository = None
    strategy_generation = None
    strategy_activation = None
    artifacts = None
    runtime = None
    storage_configured = settings.source_encryption_key_base64 is not None
    if storage_configured:
        assert settings.source_encryption_key_base64 is not None
        master_key = base64.b64decode(
            settings.source_encryption_key_base64.get_secret_value(), validate=True
        )
        protector = SourceContentProtector(
            LocalAesKeyProvider(master_key, settings.source_encryption_key_id)
        )
        generation_repository = SqlAlchemyStrategyGenerationRepository(database.sessions, protector)
        artifacts = EncryptedFilesystemArtifactStore(
            Path(settings.generated_artifact_root), protector
        )
        runtime = DockerGeneratedStrategyRuntime(
            apparmor_profile=settings.strategy_sandbox_apparmor_profile
        )
    generation_configured = storage_configured and all(
        (
            settings.llm_endpoint,
            settings.llm_model_id,
            settings.llm_model_version,
            settings.llm_api_key,
        )
    )
    if generation_configured:
        assert settings.llm_endpoint is not None
        assert settings.llm_model_id is not None
        assert settings.llm_model_version is not None
        assert settings.llm_api_key is not None
        assert generation_repository is not None
        assert artifacts is not None
        assert runtime is not None
        model = StructuredStrategyGenerationAdapter(
            client,
            endpoint=settings.llm_endpoint,
            provider=settings.llm_provider,
            model_id=settings.llm_model_id,
            model_version=settings.llm_model_version,
            api_key=settings.llm_api_key.get_secret_value(),
        )
        source_reader = SafeWebSourceAdapter(client)
        strategy_generation = GenerateStrategies(
            model, source_reader, artifacts, runtime, generation_repository, clock
        )
        strategy_activation = ActivateGeneratedStrategy(
            generation_repository,
            artifacts,
            strategy_registry,
            runtime,
            model,
            clock,
            strategy_definitions,
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
        strategy_registry=strategy_registry,
        strategy_discovery=strategy_discovery,
        strategy_analysis=strategy_analysis,
        strategy_generation_repository=generation_repository,
        strategy_generation=strategy_generation,
        strategy_activation=strategy_activation,
        generated_artifacts=artifacts,
        generated_runtime=runtime,
        strategy_definitions=strategy_definitions,
        realtime_provider=realtime_provider,
        realtime_hub=realtime_hub,
    )
