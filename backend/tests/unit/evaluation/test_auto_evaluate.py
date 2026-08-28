"""The automatic Generate/Backtest/Evaluate/Rank cycle (REQUIREMENT.md §21-§23)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from crypto_lab.application.evaluations.auto_evaluate import (
    AutoEvaluationPipeline,
    AutoEvaluationSettings,
)
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.timeframe import Timeframe

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

    async def materialize(self, selection, time_range, *, request_id=None):
        self.requested.append((selection, time_range))
        return FakeMaterialization(FakeDataset(status=self.status), building=self.building)


@dataclass
class FakeParameters:
    canonical_fingerprint: str = DIGEST
    schema_fingerprint: str = DIGEST
    values: dict[str, object] = field(default_factory=dict)


@dataclass
class FakeStrategy:
    def validate_parameters(self, raw):
        return FakeParameters()


@dataclass
class FakeMetadata:
    strategy_id: str
    strategy_type: str = "SINGLE"
    strategy_version: str = "1.0.0"
    contract_version: str = "1.0.0"


@dataclass
class FakeEntry:
    strategy_id: str
    strategy_version: str = "1.0.0"
    strategy: FakeStrategy = field(default_factory=FakeStrategy)
    metadata: FakeMetadata | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = FakeMetadata(self.strategy_id)


@dataclass
class FakeDiscovery:
    entries: tuple[FakeEntry, ...]

    def list(self, status=None):
        return self.entries


@dataclass
class FakeDefinitions:
    resolved: list[Any] = field(default_factory=list)

    async def create_or_resolve(self, definition):
        self.resolved.append(definition)
        return definition


@dataclass
class FakeProvenance:
    context_fingerprint: str = DIGEST


@dataclass
class FakeAnalysis:
    contract_version: str = "1.0.0"
    context_provenance: FakeProvenance = field(default_factory=FakeProvenance)


@dataclass
class FakeAnalyzer:
    calls: list[tuple[UUID, UUID]] = field(default_factory=list)

    async def analyze(self, definition_id, dataset_id, request_id):
        self.calls.append((definition_id, dataset_id))
        return FakeAnalysis()


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
    schema_version: str = "1"
    checksum: str = DIGEST
    selection: FakeSelection = field(default_factory=FakeSelection)
    time_range: FakeRange = field(default_factory=FakeRange)


@dataclass
class FakeBacktestDataset:
    metadata: FakeMetadataBundle = field(default_factory=FakeMetadataBundle)


@dataclass
class FakeDatasetReader:
    available: bool = True

    async def get_complete(self, dataset_id):
        return FakeBacktestDataset() if self.available else None


@dataclass
class FakeRun:
    """Mirrors BacktestRun: identity lives on the configuration."""

    configuration: Any


@dataclass
class FakeCreateBacktest:
    configurations: list[Any] = field(default_factory=list)

    async def execute(self, configuration):
        self.configurations.append(configuration)
        return FakeRun(configuration)


@dataclass
class FakeResult:
    id: UUID


@dataclass
class FakeExecuteBacktest:
    runs: list[UUID] = field(default_factory=list)

    async def execute(self, run_id, request_id):
        self.runs.append(run_id)
        return FakeResult(UUID(int=int(str(run_id.int)[-6:]) % 10_000 + 500))


@dataclass
class FakeEvaluation:
    id: UUID


@dataclass
class FakeEvaluate:
    calls: list[Any] = field(default_factory=list)

    async def execute(self, result_id, *policies):
        self.calls.append((result_id, policies))
        return FakeEvaluation(uuid4())


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


def build(**overrides: Any) -> tuple[AutoEvaluationPipeline, dict[str, Any]]:
    parts: dict[str, Any] = {
        "datasets": FakeDatasetService(),
        "dataset_reader": FakeDatasetReader(),
        "discovery": FakeDiscovery((FakeEntry("moving-average"), FakeEntry("rsi"))),
        "definitions": FakeDefinitions(),
        "analyzer": FakeAnalyzer(),
        "create_backtest": FakeCreateBacktest(),
        "execute_backtest": FakeExecuteBacktest(),
        "evaluate_backtest": FakeEvaluate(),
        "ingestion": FakeIngestion(),
    }
    parts.update(overrides)
    pipeline = AutoEvaluationPipeline(
        settings=AutoEvaluationSettings(candles=200),
        clock=FixedClock(),
        execution_policy=FakePolicy(UUID(int=1), "1.0.0"),
        evaluation_policy=FakePolicy(UUID(int=2), "1.0.0"),
        scoring_policy=FakePolicy(UUID(int=3), "1.0.0"),
        **parts,
    )
    return pipeline, parts


async def test_cycle_evaluates_every_registered_strategy_and_ranks_it() -> None:
    pipeline, parts = build()

    report = await pipeline.run_once()

    assert report.completed is True
    assert len(report.evaluated) == 2
    assert parts["ingestion"].ingested == list(report.evaluated)
    assert [item.strategy_id for item in parts["definitions"].resolved] == [
        "moving-average",
        "rsi",
    ]


async def test_window_covers_only_closed_candles() -> None:
    pipeline, parts = build()

    await pipeline.run_once()

    _, time_range = parts["datasets"].requested[0]
    assert time_range.end_time == Timeframe.FIFTEEN_MINUTES.floor(NOW)
    assert time_range.end_time < NOW
    assert (time_range.end_time - time_range.start_time).total_seconds() == 200 * 900


async def test_repeating_a_cycle_reuses_the_same_run_and_definition_identity() -> None:
    pipeline, parts = build()

    first = await pipeline.run_once()
    second = await pipeline.run_once()

    assert len(first.evaluated) == len(second.evaluated) == 2
    definitions = parts["definitions"].resolved
    assert definitions[0].id == definitions[2].id
    configurations = parts["create_backtest"].configurations
    assert configurations[0].run_id == configurations[2].run_id
    assert configurations[0].job_id == configurations[2].job_id


async def test_a_building_dataset_defers_the_cycle_without_evaluating() -> None:
    pipeline, parts = build(datasets=FakeDatasetService(building=True))

    report = await pipeline.run_once()

    assert report.dataset_building is True
    assert report.completed is False
    assert report.evaluated == ()
    assert parts["ingestion"].ingested == []


async def test_an_incomplete_dataset_stops_the_cycle() -> None:
    pipeline, _ = build(datasets=FakeDatasetService(status=DatasetStatus.INCOMPLETE))

    report = await pipeline.run_once()

    assert report.dataset_id is None
    assert report.evaluated == ()


async def test_one_failing_strategy_does_not_stop_the_others() -> None:
    class ExplodingAnalyzer(FakeAnalyzer):
        async def analyze(self, definition_id, dataset_id, request_id):
            if not self.calls:
                self.calls.append((definition_id, dataset_id))
                raise RuntimeError("analysis unavailable")
            return await super().analyze(definition_id, dataset_id, request_id)

    pipeline, parts = build(analyzer=ExplodingAnalyzer())

    report = await pipeline.run_once()

    assert len(report.failures) == 1
    assert len(report.evaluated) == 1
    assert len(parts["ingestion"].ingested) == 1


async def test_the_configured_policies_are_the_ones_applied() -> None:
    pipeline, parts = build()

    await pipeline.run_once()

    _, policies = parts["evaluate_backtest"].calls[0]
    assert policies == (UUID(int=2), "1.0.0", UUID(int=3), "1.0.0")
    assert parts["create_backtest"].configurations[0].execution_policy_id == UUID(int=1)


@pytest.mark.parametrize("initial", [Decimal("10000")])
async def test_execution_settings_reach_the_backtest_configuration(initial: Decimal) -> None:
    pipeline, parts = build()

    await pipeline.run_once()

    configuration = parts["create_backtest"].configurations[0]
    assert configuration.initial_capital == initial
    assert configuration.fee_rate == Decimal("0.0004")
    assert configuration.slippage_rate == Decimal("0.0002")
    assert configuration.random_seed == 424242
