"""The background search loop: generate, backtest, evaluate, rank, observe."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from tests.fixtures.search_repository import MemoryRepository

from crypto_lab.application.evaluations.auto_evaluate import (
    SearchLoopCycleReport,
    SearchLoopPipeline,
    SearchLoopRunner,
    SearchLoopSettings,
    SearchLoopStatus,
)
from crypto_lab.application.search_service import SearchEventHub, StrategySearchService
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.application.strategies.save_configuration import SaveStrategyConfiguration
from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.search import RandomSearchGenerator
from crypto_lab.domain.strategy.definition import StrategyDefinition

NOW = datetime(2026, 8, 28, 6, 7, 31, tzinfo=UTC)
DATASET_ID = UUID(int=41)
DIGEST = "a" * 64
START = datetime(2026, 8, 25, tzinfo=UTC)
END = datetime(2026, 8, 28, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


@dataclass
class FakeDataset:
    id: UUID = DATASET_ID
    status: DatasetStatus = DatasetStatus.COMPLETE


@dataclass
class FakeMaterialization:
    dataset: FakeDataset
    created: bool = True
    building: bool = False


@dataclass
class FakeDatasetService:
    status: DatasetStatus = DatasetStatus.COMPLETE
    building: bool = False
    requested: list[Any] = field(default_factory=list)
    dataset_id: UUID = DATASET_ID

    async def materialize(self, selection, time_range, *, request_id=None):
        self.requested.append((selection, time_range))
        return FakeMaterialization(
            FakeDataset(id=self.dataset_id, status=self.status), building=self.building
        )


@dataclass
class FakeSelection:
    provider: str = "BINANCE"
    pair: str = "BTCUSDT"
    timeframe: Timeframe = Timeframe.FIFTEEN_MINUTES


@dataclass
class FakeRange:
    start_time: datetime = START
    end_time: datetime = END


@dataclass
class FakeMetadataBundle:
    id: UUID = DATASET_ID
    schema_version: str = "1"
    checksum: str = DIGEST
    candle_count: int = 500
    selection: FakeSelection = field(default_factory=FakeSelection)
    time_range: FakeRange = field(default_factory=FakeRange)


@dataclass
class FakeBacktestDataset:
    metadata: FakeMetadataBundle = field(default_factory=FakeMetadataBundle)


@dataclass
class FakeDatasetReader:
    available: bool = True

    async def get_complete(self, dataset_id):
        return FakeBacktestDataset(FakeMetadataBundle(id=dataset_id)) if self.available else None


@dataclass
class FakeDefinitionRepository:
    """Mimics the real repository's content-addressed create_or_resolve."""

    by_fingerprint: dict[str, StrategyDefinition] = field(default_factory=dict)
    resolved: list[StrategyDefinition] = field(default_factory=list)

    async def create_or_resolve(self, definition: StrategyDefinition) -> StrategyDefinition:
        existing = self.by_fingerprint.get(definition.content_fingerprint)
        if existing is not None:
            self.resolved.append(existing)
            return existing
        self.by_fingerprint[definition.content_fingerprint] = definition
        self.resolved.append(definition)
        return definition

    async def find_exact(self, strategy_id, strategy_version):
        return ()


@dataclass
class FakeConfigurationRepository:
    """Mimics the real repository's content-addressed save."""

    by_key: dict[str, Any] = field(default_factory=dict)
    saved: list[Any] = field(default_factory=list)

    async def save(self, configuration):
        existing = self.by_key.get(configuration.configuration_key)
        if existing is not None:
            self.saved.append(existing)
            return existing
        self.by_key[configuration.configuration_key] = configuration
        self.saved.append(configuration)
        return configuration


@dataclass
class FakeProvenance:
    context_fingerprint: str = DIGEST
    sentiment: tuple = ()


@dataclass
class FakeAnalysis:
    strategy_definition: Any
    contract_version: str = "1.0.0"
    context_provenance: FakeProvenance = field(default_factory=FakeProvenance)


@dataclass
class FakeAnalyzer:
    """Resolves an analysis straight from what the definition repository stored."""

    definitions: FakeDefinitionRepository
    calls: list[tuple[UUID, UUID]] = field(default_factory=list)

    async def analyze(self, definition_id, dataset_id, request_id):
        self.calls.append((definition_id, dataset_id))
        definition = next(
            item for item in self.definitions.by_fingerprint.values() if item.id == definition_id
        )
        return FakeAnalysis(strategy_definition=definition)


@dataclass
class FakeRun:
    configuration: Any


@dataclass
class FakeCreateBacktest:
    configurations: list[Any] = field(default_factory=list)
    fail_at_call: int | None = None

    async def execute(self, configuration):
        self.configurations.append(configuration)
        if self.fail_at_call is not None and len(self.configurations) == self.fail_at_call:
            raise RuntimeError("synthetic backtest failure")
        return FakeRun(configuration)


@dataclass
class FakeResult:
    id: UUID


@dataclass
class FakeExecuteBacktest:
    runs: list[UUID] = field(default_factory=list)

    async def execute(self, run_id, request_id, *, resume_interrupted=False):
        self.runs.append(run_id)
        return FakeResult(UUID(int=int(str(run_id.int)[-6:]) % 10_000 + 500))


@dataclass
class FakeEvaluation:
    id: UUID
    score: Decimal


@dataclass
class FakeEvaluate:
    calls: list[Any] = field(default_factory=list)
    _next: int = 0

    async def execute(self, result_id, *policies):
        self.calls.append((result_id, policies))
        self._next += 1
        return FakeEvaluation(uuid4(), Decimal(self._next))


@dataclass
class FakeIngestion:
    ingested: list[UUID] = field(default_factory=list)

    async def on_evaluation_completed(self, evaluation_result_id, *, request_id=None):
        self.ingested.append(evaluation_result_id)
        return ()


@dataclass
class FakePolicy:
    id: UUID
    version: str


def build(**overrides: Any) -> tuple[SearchLoopPipeline, dict[str, Any]]:
    registry = build_strategy_registry()
    clock = FixedClock()
    definitions = FakeDefinitionRepository()
    configurations = FakeConfigurationRepository()
    parts: dict[str, Any] = {
        "datasets": FakeDatasetService(),
        "dataset_reader": FakeDatasetReader(),
        "discovery": DiscoverStrategies(registry),
        "generator": RandomSearchGenerator(registry),
        "configurations": SaveStrategyConfiguration(registry, definitions, configurations, clock),
        "create_backtest": FakeCreateBacktest(),
        "execute_backtest": FakeExecuteBacktest(),
        "evaluate_backtest": FakeEvaluate(),
        "ingestion": FakeIngestion(),
    }
    parts.update(overrides)
    parts["analyzer"] = overrides.get("analyzer", FakeAnalyzer(definitions))
    repository = overrides.get("repository", MemoryRepository())
    search = StrategySearchService(
        repository=repository,
        generator=parts["generator"],
        configurations=parts["configurations"],
        datasets=parts["dataset_reader"],
        analyzer=parts["analyzer"],
        create_backtest=parts["create_backtest"],
        execute_backtest=parts["execute_backtest"],
        evaluate_backtest=parts["evaluate_backtest"],
        leaderboard=parts["ingestion"],
        clock=clock,
        hub=SearchEventHub(),
        execution_policy=FakePolicy(UUID(int=1), "1.0.0"),
        evaluation_policy=FakePolicy(UUID(int=2), "1.0.0"),
        scoring_policy=FakePolicy(UUID(int=3), "1.0.0"),
    )
    parts["search"] = search
    parts["repository"] = repository
    pipeline = SearchLoopPipeline(
        settings=SearchLoopSettings(candles=200, candidates_per_cycle=3),
        clock=clock,
        datasets=parts["datasets"],
        discovery=parts["discovery"],
        search=search,
    )
    extras = {"definitions": definitions, "configuration_repo": configurations, **parts}
    return pipeline, extras


async def test_a_cycle_generates_genuinely_new_candidates_and_feeds_the_leaderboard() -> None:
    pipeline, parts = build()

    report = await pipeline.run_cycle(0)

    assert report.completed is True
    assert report.generated == 3
    assert report.succeeded == 3
    assert report.failed == 0
    assert len(parts["ingestion"].ingested) == 3
    # Candidates come from the generator, not from replaying single registered
    # strategies: every configuration saved is a composite of >= 2 strategies.
    assert all(len(saved.members) >= 2 for saved in parts["configuration_repo"].saved)


async def test_a_failing_candidate_does_not_stop_the_rest_of_the_cycle() -> None:
    pipeline, parts = build(create_backtest=FakeCreateBacktest(fail_at_call=2))

    report = await pipeline.run_cycle(0)

    assert report.generated == 3
    assert report.succeeded == 2
    assert report.failed == 1
    assert len(parts["ingestion"].ingested) == 2


async def test_a_building_dataset_defers_the_cycle_without_evaluating() -> None:
    pipeline, parts = build(datasets=FakeDatasetService(building=True))

    report = await pipeline.run_cycle(0)

    assert report.dataset_building is True
    assert report.completed is False
    assert report.generated == 0
    assert parts["ingestion"].ingested == []


async def test_repeating_a_cycle_is_idempotent() -> None:
    """DoD: re-running a cycle resolves the same identity instead of duplicating work."""

    pipeline, parts = build()

    first = await pipeline.run_cycle(7)
    second = await pipeline.run_cycle(7)

    assert first.generated == second.generated == 3
    assert first.succeeded == second.succeeded == 3

    configurations = parts["create_backtest"].configurations
    assert len(configurations) == 3
    assert len(parts["execute_backtest"].runs) == 3
    assert len(parts["repository"].runs) == 1
    assert (await pipeline.snapshot()).candidates_succeeded == 3


async def test_a_different_cycle_index_produces_a_different_identity() -> None:
    pipeline, _ = build()

    first = await pipeline.run_cycle(1)
    second = await pipeline.run_cycle(2)

    assert first.generated == second.generated == 3


async def test_restarting_cycle_zero_on_a_new_dataset_creates_new_runs() -> None:
    datasets = FakeDatasetService()
    pipeline, parts = build(datasets=datasets)
    await pipeline.run_cycle(0)
    datasets.dataset_id = UUID(int=42)
    restarted, _ = build(datasets=datasets, repository=parts["repository"])
    assert await restarted.restore() == 1
    await pipeline.run_cycle(await restarted.restore())
    configurations = parts["create_backtest"].configurations
    before = configurations[:3]
    after = configurations[3:]
    assert {run.run_id for run in before}.isdisjoint(run.run_id for run in after)
    assert all(run.dataset_id == UUID(int=42) for run in after)


@dataclass
class CountingPipeline:
    calls: list[int] = field(default_factory=list)

    async def run_cycle(self, cycle_index: int, *, request_id: str | None = None):
        self.calls.append(cycle_index)
        return SearchLoopCycleReport(cycle_index, DATASET_ID, False, 1, 1, 0, Decimal("1"), "x")


def test_pause_and_resume_flip_status_without_touching_counters() -> None:
    runner = SearchLoopRunner(
        CountingPipeline(), FixedClock(), interval_seconds=999, retry_seconds=999
    )

    assert runner.status().status == SearchLoopStatus.STOPPED

    runner.pause()
    assert runner.status().status == SearchLoopStatus.PAUSED

    runner.resume()
    assert runner.status().status == SearchLoopStatus.RUNNING


async def test_pause_stops_new_cycles_and_resume_restarts_them() -> None:
    pipeline = CountingPipeline()
    runner = SearchLoopRunner(pipeline, FixedClock(), interval_seconds=0.03, retry_seconds=0.03)
    try:
        runner.start()
        await asyncio.sleep(0.16)
        assert runner.status().status == SearchLoopStatus.RUNNING
        calls_before_pause = len(pipeline.calls)
        assert calls_before_pause > 0

        runner.pause()
        assert runner.status().status == SearchLoopStatus.PAUSED
        await asyncio.sleep(0.16)
        assert len(pipeline.calls) == calls_before_pause

        runner.resume()
        await asyncio.sleep(0.16)
        assert len(pipeline.calls) > calls_before_pause

        stats = runner.status()
        assert stats.candidates_generated == stats.cycles_completed
    finally:
        await runner.stop()

    assert runner.status().status == SearchLoopStatus.STOPPED


async def test_generation_failure_is_persisted_and_not_counted_as_a_completed_cycle():
    class BrokenGenerator:
        generator_id, version = "broken", "1.0.0"

        def generate(self, *args):
            raise ValueError("invalid search space")

    pipeline, parts = build(generator=BrokenGenerator())
    report = await pipeline.run_cycle(0)
    assert report.completed is False
    assert report.error == "invalid search space"
    stats = await pipeline.snapshot()
    assert stats.cycles_completed == 0
    assert stats.last_error == report.error
    assert await pipeline.restore() == 1


async def test_restart_consumes_stored_queue_and_reconciles_completed_candidates():
    pipeline, parts = build()
    await pipeline.run_cycle(0)
    repository = parts["repository"]
    run = next(iter(repository.runs.values()))
    # Simulate shutdown after candidate 1 was committed but before its counter update.
    run.status, run.succeeded = "RUNNING", 0
    for item in repository.items[1:]:
        item.status = "QUEUED"

    class UnavailableGenerator:
        generator_id, version = "random-search", "1.0.0"

        def generate(self, *args):
            raise AssertionError("A durable queue must not be regenerated")

    restarted, fresh = build(repository=repository, generator=UnavailableGenerator())
    assert await restarted.restore() == 0
    report = await restarted.run_cycle(0)
    assert report.succeeded == 3
    assert len(fresh["execute_backtest"].runs) == 2
    assert len(repository.runs) == 1
    assert len(repository.items) == 3
    assert (await restarted.snapshot()).candidates_succeeded == 3
