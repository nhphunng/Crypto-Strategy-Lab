from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from crypto_lab.api.leaderboard_dependencies import (
    LeaderboardContainer,
    build_leaderboard_container,
)
from crypto_lab.application.backtests.create_run import CreateBacktestRun
from crypto_lab.application.backtests.execute_run import ExecuteBacktestRun
from crypto_lab.application.backtests.get_result import GetBacktestResult
from crypto_lab.application.backtests.ports import BacktestDataset, StrategyAnalyzer
from crypto_lab.application.evaluations.auto_evaluate import (
    AutoEvaluationLoop,
    AutoEvaluationPipeline,
    AutoEvaluationSettings,
    SearchLoopPipeline,
    SearchLoopRunner,
    SearchLoopSettings,
)
from crypto_lab.application.evaluations.compare_results import CompareEvaluationResults
from crypto_lab.application.evaluations.evaluate_result import EvaluateBacktestResult
from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.market_data.ports import (
    Clock,
    MarketDataRepository,
    RealtimeMarketDataProvider,
)
from crypto_lab.application.news.collect_news import CollectNews
from crypto_lab.application.news.collection_loop import NewsCollectionLoop
from crypto_lab.application.news.list_news import ListNews
from crypto_lab.application.search_service import SearchEventHub, StrategySearchService
from crypto_lab.application.sentiment.analyze_pending_news import AnalyzePendingNews
from crypto_lab.application.sentiment.sentiment_loop import SentimentAnalysisLoop
from crypto_lab.application.strategies.activate_generated_strategy import ActivateGeneratedStrategy
from crypto_lab.application.strategies.analyze_strategy import AnalyzeStrategy
from crypto_lab.application.strategies.combine_configuration import ConfiguredStrategyAnalyzer
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.application.strategies.generate_strategies import GenerateStrategies
from crypto_lab.application.strategies.ports import (
    GeneratedArtifactStore,
    StrategyDefinitionRepository,
    StrategyGenerationRepository,
)
from crypto_lab.application.strategies.save_configuration import SaveStrategyConfiguration
from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.backtest.configuration import ExecutionPolicy
from crypto_lab.domain.evaluation.policy import (
    EvaluationPolicy,
    MetricDirection,
    MetricWeight,
    ScoringPolicy,
)
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.news.coin_resolution import CoinResolver
from crypto_lab.domain.search import RandomSearchGenerator
from crypto_lab.domain.sentiment.model import ModelRef
from crypto_lab.domain.strategy.errors import StrategyError
from crypto_lab.domain.strategy.implementations.news_sentiment import NewsSentimentStrategy
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion
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
from crypto_lab.infrastructure.news.rss_provider import (
    RssFeedDefinition,
    RssNewsProvider,
)
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from crypto_lab.infrastructure.persistence.repositories.backtest_repository import (
    SqlAlchemyBacktestRepository,
)
from crypto_lab.infrastructure.persistence.repositories.evaluation_repository import (
    SqlAlchemyEvaluationRepository,
)
from crypto_lab.infrastructure.persistence.repositories.news_repository import (
    SqlAlchemyNewsRepository,
)
from crypto_lab.infrastructure.persistence.repositories.search_repository import (
    SqlAlchemySearchRepository,
)
from crypto_lab.infrastructure.persistence.repositories.sentiment_repository import (
    SqlAlchemySentimentAnalysisRepository,
)
from crypto_lab.infrastructure.persistence.repositories.strategy_configuration_repository import (
    SqlAlchemyStrategyConfigurationRepository,
)
from crypto_lab.infrastructure.persistence.repositories.strategy_definition_repository import (
    SqlAlchemyStrategyDefinitionRepository,
)
from crypto_lab.infrastructure.persistence.repositories.strategy_generation_repository import (
    SqlAlchemyStrategyGenerationRepository,
)
from crypto_lab.infrastructure.persistence.sentiment_context_reader import (
    SqlAlchemySentimentContextReader,
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
from crypto_lab.infrastructure.sentiment.lexicon_analyzer import LexiconSentimentAnalyzer
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.infrastructure.sources.web_source_adapter import SafeWebSourceAdapter

EXECUTION_POLICY = ExecutionPolicy(
    uuid5(NAMESPACE_URL, "crypto-lab/execution/next-open-v1"),
    "next-open-long-only",
    "1.0.0",
)
EVALUATION_POLICY = EvaluationPolicy(
    uuid5(NAMESPACE_URL, "crypto-lab/evaluation/standard-v1"),
    "standard-metrics",
    "1.0.0",
)
# The exact model identity NewsSentimentStrategy reads under -- must match
# LexiconSentimentAnalyzer's own model_id/model_version.
SENTIMENT_MODEL = ModelRef(model_id="lexicon-sentiment", model_version="1.0.0")
BALANCED_SCORING_POLICY = ScoringPolicy(
    uuid5(NAMESPACE_URL, "crypto-lab/scoring/balanced-v1"),
    "balanced",
    "1.0.0",
    "Balanced v1",
    (
        MetricWeight(
            "totalReturn",
            MetricDirection.HIGHER,
            Decimal("-100"),
            Decimal("100"),
            Decimal("0.35"),
        ),
        MetricWeight(
            "winRate",
            MetricDirection.HIGHER,
            Decimal("0"),
            Decimal("100"),
            Decimal("0.25"),
        ),
        MetricWeight(
            "maxDrawdown",
            MetricDirection.LOWER,
            Decimal("0"),
            Decimal("100"),
            Decimal("0.25"),
        ),
        MetricWeight(
            "sharpeRatio",
            MetricDirection.HIGHER,
            Decimal("-3"),
            Decimal("3"),
            Decimal("0.15"),
        ),
    ),
    (
        "totalReturn:desc",
        "maxDrawdown:asc",
        "winRate:desc",
        "evaluationResultId:asc",
    ),
)


class BacktestDatasetReader:
    def __init__(self, repository: SqlAlchemyMarketDataRepository) -> None:
        self._repository = repository

    async def get_complete(self, dataset_id: UUID) -> BacktestDataset | None:
        dataset = await self._repository.get_dataset(dataset_id, verify=True)
        if dataset is None or not dataset.consumer_eligible:
            return None
        page = await self._repository.list_dataset_candles(
            dataset_id, None, dataset.candle_count or 1
        )
        return BacktestDataset(dataset, page.candles)


class BacktestStrategyAnalyzer:
    def __init__(self, service: AnalyzeStrategy) -> None:
        self._service = service

    async def analyze(
        self, definition_id: UUID, dataset_id: UUID, request_id: str
    ) -> StrategyAnalysisResult:
        from crypto_lab.application.strategies.analyze_strategy import AnalyzeStrategyCommand

        return await self._service.execute(
            AnalyzeStrategyCommand(
                request_id,
                definition_id,
                str(dataset_id),
                ContractVersionRange(1, 0, 0),
            )
        )


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
    strategy_configurations: SqlAlchemyStrategyConfigurationRepository | None = None
    save_strategy_configuration: SaveStrategyConfiguration | None = None
    realtime_provider: RealtimeMarketDataProvider | None = None
    realtime_hub: RealtimeSelectionHub | None = None
    backtest_repository: SqlAlchemyBacktestRepository | None = None
    backtest_datasets: BacktestDatasetReader | None = None
    backtest_strategy_analyzer: StrategyAnalyzer | None = None
    create_backtest: CreateBacktestRun | None = None
    execute_backtest: ExecuteBacktestRun | None = None
    get_backtest: GetBacktestResult | None = None
    evaluation_repository: SqlAlchemyEvaluationRepository | None = None
    evaluate_backtest: EvaluateBacktestResult | None = None
    compare_evaluations: CompareEvaluationResults | None = None
    news_repository: SqlAlchemyNewsRepository | None = None
    list_news: ListNews | None = None
    collect_news: CollectNews | None = None
    news_collection_loop: NewsCollectionLoop | None = None
    sentiment_repository: SqlAlchemySentimentAnalysisRepository | None = None
    sentiment_context_reader: SqlAlchemySentimentContextReader | None = None
    sentiment_analyzer: LexiconSentimentAnalyzer | None = None
    analyze_pending_news: AnalyzePendingNews | None = None
    sentiment_loop: SentimentAnalysisLoop | None = None
    search_repository: SqlAlchemySearchRepository | None = None
    search_hub: SearchEventHub | None = None
    strategy_search: StrategySearchService | None = None

    async def initialize_backtest_evaluation(self) -> None:
        if self.backtest_repository is None or self.evaluation_repository is None:
            return
        now = self.clock.now()
        await self.backtest_repository.ensure_policy(EXECUTION_POLICY, now)
        await self.evaluation_repository.ensure_policies(
            EVALUATION_POLICY, BALANCED_SCORING_POLICY, now
        )

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
                raise RuntimeError(
                    "activated generated-strategy provenance has missing durable references"
                )
            stored_artifact = await self.generated_artifacts.get(metadata.content_fingerprint)
            artifact = replace(
                stored_artifact,
                id=metadata.id,
                draft_id=metadata.draft_id,
            )
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

    leaderboard: LeaderboardContainer | None = None
    auto_evaluation: AutoEvaluationLoop | None = None
    search_loop: SearchLoopRunner | None = None

    async def close(self) -> None:
        if self.search_loop is not None:
            await self.search_loop.stop()
        if self.news_collection_loop is not None:
            await self.news_collection_loop.stop()
        if self.sentiment_loop is not None:
            await self.sentiment_loop.stop()
        if self.strategy_search is not None:
            await self.strategy_search.close()
        if self.realtime_hub is not None:
            await self.realtime_hub.close()
        if self.http_client is not None:
            await self.http_client.aclose()
        if self.generated_runtime is not None:
            await self.generated_runtime.close()
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
    historical = HistoricalMarketDataService(
        repository,
        provider,
        clock,
        supported_pairs=frozenset(settings.capabilities.pairs),
        supported_timeframes=frozenset(settings.capabilities.timeframes),
    )
    datasets = DatasetService(
        repository,
        historical,
        clock,
        lease_duration=timedelta(seconds=settings.dataset_build_lease_seconds),
        max_dataset_candles=settings.max_dataset_candles,
    )
    strategy_registry = build_strategy_registry()
    sentiment_repository = SqlAlchemySentimentAnalysisRepository(database.sessions)
    sentiment_context_reader = SqlAlchemySentimentContextReader(database.sessions)
    sentiment_analyzer = LexiconSentimentAnalyzer()
    strategy_registry.register(NewsSentimentStrategy(sentiment_context_reader, SENTIMENT_MODEL))
    strategy_discovery = DiscoverStrategies(strategy_registry)
    strategy_definitions = SqlAlchemyStrategyDefinitionRepository(database.sessions)
    strategy_configurations = SqlAlchemyStrategyConfigurationRepository(database.sessions)
    save_strategy_configuration = SaveStrategyConfiguration(
        strategy_registry, strategy_definitions, strategy_configurations, clock
    )
    strategy_contexts = SqlAlchemyStrategyContextReader(repository)
    strategy_analysis = AnalyzeStrategy(
        strategy_definitions,
        strategy_contexts,
        strategy_registry,
    )
    backtest_repository = SqlAlchemyBacktestRepository(database.sessions)
    backtest_datasets = BacktestDatasetReader(repository)
    backtest_strategy_analyzer = ConfiguredStrategyAnalyzer(
        strategy_analysis, strategy_configurations, strategy_definitions
    )
    create_backtest = CreateBacktestRun(backtest_repository, clock)
    execute_backtest = ExecuteBacktestRun(
        backtest_repository,
        backtest_datasets,
        backtest_strategy_analyzer,
        backtest_repository,
        clock,
    )
    get_backtest = GetBacktestResult(backtest_repository)
    evaluation_repository = SqlAlchemyEvaluationRepository(database.sessions, backtest_repository)
    evaluate_backtest = EvaluateBacktestResult(
        backtest_repository,
        evaluation_repository,
        evaluation_repository,
        clock,
    )
    compare_evaluations = CompareEvaluationResults(evaluation_repository)
    news_repository = SqlAlchemyNewsRepository(database.sessions)
    list_news = ListNews(news_repository, clock)
    collect_news = None
    news_collection_loop = None
    if settings.news_collection_enabled:
        coin_resolver = CoinResolver()
        rss_feeds = tuple(
            RssFeedDefinition(source=feed.source, url=feed.url) for feed in settings.news_feeds
        )
        rss_provider = RssNewsProvider(client, rss_feeds, clock, coin_resolver)
        collect_news = CollectNews((rss_provider,), news_repository, clock=clock)
        news_collection_loop = NewsCollectionLoop(
            collect_news,
            interval_seconds=settings.news_collection_interval_seconds,
        )
    analyze_pending_news = AnalyzePendingNews(
        analyzer=sentiment_analyzer, repository=sentiment_repository, clock=clock
    )
    sentiment_loop = None
    if settings.sentiment_analysis_enabled:
        sentiment_loop = SentimentAnalysisLoop(
            analyze_pending_news,
            interval_seconds=settings.sentiment_analysis_interval_seconds,
            batch_size=settings.sentiment_analysis_batch_size,
        )
    generation_repository = None
    strategy_generation = None
    strategy_activation = None
    artifacts = None
    runtime = None
    source_encryption_key = settings.source_encryption_key_base64
    llm_api_key = settings.llm_api_key
    storage_configured = source_encryption_key is not None
    if storage_configured:
        assert source_encryption_key is not None
        master_key = base64.b64decode(source_encryption_key.get_secret_value(), validate=True)
        protector = SourceContentProtector(
            LocalAesKeyProvider(master_key, settings.source_encryption_key_id)
        )
        generation_repository = SqlAlchemyStrategyGenerationRepository(database.sessions, protector)
        artifacts = EncryptedFilesystemArtifactStore(
            Path(settings.generated_artifact_root), protector
        )
        runtime = DockerGeneratedStrategyRuntime(
            image=settings.strategy_sandbox_image,
            apparmor_profile=settings.strategy_sandbox_apparmor_profile,
            engine_url=settings.strategy_sandbox_engine_url,
        )
    generation_configured = storage_configured and all(
        (
            settings.llm_endpoint,
            settings.llm_model_id,
            settings.llm_model_version,
            llm_api_key,
            settings.llm_data_policy_confirmed,
        )
    )
    if generation_configured:
        assert settings.llm_endpoint is not None
        assert settings.llm_model_id is not None
        assert settings.llm_model_version is not None
        assert llm_api_key is not None
        assert generation_repository is not None
        assert artifacts is not None
        assert runtime is not None
        model = StructuredStrategyGenerationAdapter(
            client,
            endpoint=settings.llm_endpoint,
            provider=settings.llm_provider,
            model_id=settings.llm_model_id,
            model_version=settings.llm_model_version,
            api_key=llm_api_key.get_secret_value(),
            connect_timeout_seconds=settings.llm_connect_timeout_seconds,
            read_timeout_seconds=settings.llm_read_timeout_seconds,
            max_attempts=settings.llm_max_attempts,
            max_retry_delay_seconds=settings.llm_max_retry_delay_seconds,
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
    leaderboard = build_leaderboard_container(database)
    search_repository = SqlAlchemySearchRepository(database.sessions)
    search_hub = SearchEventHub()
    strategy_search = StrategySearchService(
        repository=search_repository,
        generator=RandomSearchGenerator(strategy_registry),
        configurations=save_strategy_configuration,
        datasets=backtest_datasets,
        analyzer=backtest_strategy_analyzer,
        create_backtest=create_backtest,
        execute_backtest=execute_backtest,
        evaluate_backtest=evaluate_backtest,
        leaderboard=leaderboard.ingestion,
        clock=clock,
        hub=search_hub,
        execution_policy=EXECUTION_POLICY,
        evaluation_policy=EVALUATION_POLICY,
        scoring_policy=BALANCED_SCORING_POLICY,
    )
    auto_evaluation = _build_auto_evaluation(
        settings,
        clock,
        datasets=datasets,
        dataset_reader=backtest_datasets,
        discovery=strategy_discovery,
        definitions=strategy_definitions,
        analyzer=backtest_strategy_analyzer,
        create_backtest=create_backtest,
        execute_backtest=execute_backtest,
        evaluate_backtest=evaluate_backtest,
        ingestion=leaderboard.ingestion,
    )
    search_loop = _build_search_loop(
        settings,
        clock,
        datasets=datasets,
        dataset_reader=backtest_datasets,
        discovery=strategy_discovery,
        generator=RandomSearchGenerator(strategy_registry),
        configurations=save_strategy_configuration,
        analyzer=backtest_strategy_analyzer,
        create_backtest=create_backtest,
        execute_backtest=execute_backtest,
        evaluate_backtest=evaluate_backtest,
        ingestion=leaderboard.ingestion,
    )
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
        strategy_configurations=strategy_configurations,
        save_strategy_configuration=save_strategy_configuration,
        realtime_provider=realtime_provider,
        realtime_hub=realtime_hub,
        backtest_repository=backtest_repository,
        backtest_datasets=backtest_datasets,
        backtest_strategy_analyzer=backtest_strategy_analyzer,
        create_backtest=create_backtest,
        execute_backtest=execute_backtest,
        get_backtest=get_backtest,
        evaluation_repository=evaluation_repository,
        evaluate_backtest=evaluate_backtest,
        compare_evaluations=compare_evaluations,
        news_repository=news_repository,
        list_news=list_news,
        collect_news=collect_news,
        news_collection_loop=news_collection_loop,
        sentiment_repository=sentiment_repository,
        sentiment_context_reader=sentiment_context_reader,
        sentiment_analyzer=sentiment_analyzer,
        analyze_pending_news=analyze_pending_news,
        sentiment_loop=sentiment_loop,
        search_repository=search_repository,
        search_hub=search_hub,
        strategy_search=strategy_search,
        leaderboard=leaderboard,
        auto_evaluation=auto_evaluation,
        search_loop=search_loop,
    )


def _build_auto_evaluation(
    settings: Settings,
    clock: Clock,
    **collaborators: Any,
) -> AutoEvaluationLoop | None:
    """Wire the pipeline only when the deployment asks for it."""

    if not settings.auto_evaluation_enabled:
        return None
    pipeline = AutoEvaluationPipeline(
        settings=AutoEvaluationSettings(
            pair=settings.auto_evaluation_pair,
            timeframe=Timeframe(settings.auto_evaluation_timeframe),
            candles=settings.auto_evaluation_candles,
            interval_seconds=settings.auto_evaluation_interval_seconds,
        ),
        clock=clock,
        execution_policy=EXECUTION_POLICY,
        evaluation_policy=EVALUATION_POLICY,
        scoring_policy=BALANCED_SCORING_POLICY,
        **collaborators,
    )
    return AutoEvaluationLoop(
        pipeline,
        interval_seconds=settings.auto_evaluation_interval_seconds,
    )


def _build_search_loop(
    settings: Settings,
    clock: Clock,
    **collaborators: Any,
) -> SearchLoopRunner | None:
    """Wire the background candidate-search loop only when the deployment asks for it."""

    if not settings.search_loop_enabled:
        return None
    pipeline = SearchLoopPipeline(
        settings=SearchLoopSettings(
            pair=settings.search_loop_pair,
            timeframe=Timeframe(settings.search_loop_timeframe),
            candles=settings.search_loop_candles,
            candidates_per_cycle=settings.search_loop_candidates_per_cycle,
            minimum_size=settings.search_loop_minimum_size,
            maximum_size=settings.search_loop_maximum_size,
            base_seed=settings.search_loop_base_seed,
            interval_seconds=settings.search_loop_interval_seconds,
        ),
        clock=clock,
        execution_policy=EXECUTION_POLICY,
        evaluation_policy=EVALUATION_POLICY,
        scoring_policy=BALANCED_SCORING_POLICY,
        **collaborators,
    )
    return SearchLoopRunner(
        pipeline,
        clock,
        interval_seconds=settings.search_loop_interval_seconds,
    )
