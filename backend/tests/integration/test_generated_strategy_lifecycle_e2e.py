"""Deterministic generated-strategy lifecycle proof, run against real Postgres and the
real sandbox runtime (no live LLM, no live market-data provider).

Flow verified: deterministic LLM fixture -> generate draft -> validation -> activate
-> catalog -> analyze -> backtest -> restart -> reuse (without the LLM/source adapters).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from crypto_lab.api.dependencies import BacktestDatasetReader, BacktestStrategyAnalyzer
from crypto_lab.application.backtests.create_run import CreateBacktestRun
from crypto_lab.application.backtests.execute_run import ExecuteBacktestRun
from crypto_lab.application.market_data.dataset_service import DatasetService
from crypto_lab.application.market_data.historical_service import HistoricalMarketDataService
from crypto_lab.application.strategies.activate_generated_strategy import (
    ActivateGeneratedStrategy,
    ActivateGeneratedStrategyCommand,
)
from crypto_lab.application.strategies.analyze_strategy import (
    AnalyzeStrategy,
    AnalyzeStrategyCommand,
)
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.application.strategies.generate_strategies import (
    GenerateStrategies,
    GenerateStrategiesCommand,
)
from crypto_lab.domain.backtest.configuration import BacktestConfiguration, ExecutionPolicy
from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.generation import GenerationSourceType
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from crypto_lab.infrastructure.persistence.repositories.backtest_repository import (
    SqlAlchemyBacktestRepository,
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
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=UTC)

# A generated strategy with zero imports: BUY/SELL only on a strict close-over-close
# crossing, deterministic and prefix-stable (no look-ahead) by construction.
GENERATED_SOURCE = """def analyze(payload):
    candles = payload["context"]["candles"]
    signals = []
    previous = None
    for candle in candles:
        close = float(candle["close"])
        if previous is None:
            signals.append({"action": "HOLD", "phase": "WARMUP", "reason": "warmup"})
        elif close > previous:
            signals.append({"action": "BUY", "phase": "EVALUATED", "reason": "close rose"})
        elif close < previous:
            signals.append({"action": "SELL", "phase": "EVALUATED", "reason": "close fell"})
        else:
            signals.append({"action": "HOLD", "phase": "EVALUATED", "reason": "close flat"})
        previous = close
    return {"signals": signals}
"""


@dataclass
class FixtureCandidate:
    normalized_name: str
    display_name: str = "Fixture Lifecycle Strategy"
    description: str = "Deterministic fixture for the generated-strategy lifecycle test."
    structured_rules: dict[str, object] = field(default_factory=lambda: {"entry": "close crossing"})
    parameter_schema: ParameterSchema = field(default_factory=lambda: ParameterSchema(()))
    assumptions: tuple[str, ...] = ("Closed candles only.",)
    evidence: tuple[object, ...] = ("deterministic fixture",)
    source_code: str = GENERATED_SOURCE


class FixtureModel:
    """Stands in for the live LLM provider: no network call, always the same output."""

    provider = "deterministic-fixture"
    model_id = "fixture-model"
    model_version = "1"
    prompt_template_version = "fixture-prompt-v1"

    def __init__(self, normalized_name: str) -> None:
        self._normalized_name = normalized_name
        self.calls = 0

    async def generate(self, source_type, inert_content, request_id):
        self.calls += 1
        return [FixtureCandidate(self._normalized_name)]


class _UnusedSourceReader:
    async def prepare(self, url, request_id):
        raise AssertionError("STRATEGY_NAME requests must not fetch external sources")


class FakeHistoricalProvider:
    """Deterministic in-process candle series: no live Binance / network dependency."""

    provider = "BINANCE"

    def __init__(self, closes: list[str]) -> None:
        self._closes = closes

    async def iter_historical(self, selection: MarketSelection, time_range: TimeRange):
        candles = []
        cursor = time_range.start_time
        for close_text in self._closes:
            if cursor >= time_range.end_time:
                break
            close = Decimal(close_text)
            candles.append(
                Candle(
                    provider=selection.provider,
                    pair=selection.pair,
                    timeframe=selection.timeframe,
                    open_time=cursor,
                    close_time=selection.timeframe.close_time(cursor),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=Decimal("1"),
                    closed=True,
                    received_at=cursor + selection.timeframe.duration,
                )
            )
            cursor += selection.timeframe.duration
        yield tuple(candles)


class _Clock:
    def now(self) -> datetime:
        return NOW


def _sandbox_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        daemon = subprocess.run(
            ["docker", "info"], capture_output=True, timeout=10, check=False
        )
        image = subprocess.run(
            ["docker", "image", "inspect", "crypto-lab-strategy-sandbox:1"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return daemon.returncode == 0 and image.returncode == 0


async def test_deterministic_lifecycle_generate_activate_analyze_backtest_restart_reuse(
    tmp_path: Path,
) -> None:
    if not _sandbox_available():
        pytest.skip("Docker daemon or prebuilt sandbox image is unavailable")
    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")

    protector = SourceContentProtector(LocalAesKeyProvider(os.urandom(32), "test-lifecycle-key"))
    generation_repository = SqlAlchemyStrategyGenerationRepository(database.sessions, protector)
    artifacts = EncryptedFilesystemArtifactStore(tmp_path / "artifacts", protector)
    runtime = DockerGeneratedStrategyRuntime()
    clock = _Clock()
    strategy_id = "lifecycle-fixture-" + uuid4().hex[:8]
    model = FixtureModel(strategy_id)

    # generate: deterministic LLM fixture, no network call.
    generate = GenerateStrategies(
        model, _UnusedSourceReader(), artifacts, runtime, generation_repository, clock
    )
    request, drafts = await generate.execute(
        GenerateStrategiesCommand(GenerationSourceType.STRATEGY_NAME, strategy_id)
    )
    assert model.calls == 1
    assert len(drafts) == 1
    draft = drafts[0]

    # validation: real sandbox runtime (static + behavior checks), already ran inside
    # generate.execute(); confirm it actually passed and is ready for human review.
    assert draft.status.value == "READY_FOR_CONFIRMATION"
    report = await generation_repository.get_report(draft.validation_report_id)
    assert report is not None and report.passed

    # review + activate: exact fingerprints, explicit confirmation, atomic persistence.
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    definitions = SqlAlchemyStrategyDefinitionRepository(database.sessions)
    activate = ActivateGeneratedStrategy(
        generation_repository, artifacts, registry, runtime, model, clock, definitions
    )
    provenance = await activate.execute(
        ActivateGeneratedStrategyCommand(
            draft.id,
            draft.draft_fingerprint,
            report.artifact_fingerprint,
            report.id,
            confirmed=True,
        )
    )

    # catalog: the generated strategy is discoverable like any built-in one.
    discovery = DiscoverStrategies(registry)
    catalog = discovery.list()
    assert any(
        entry.metadata.strategy_id == strategy_id and entry.metadata.origin.value == "LLM_GENERATED"
        for entry in catalog
    )

    definition = await definitions.find_exact(
        provenance.strategy_id, SemanticVersion.parse(provenance.strategy_version)
    )
    assert len(definition) == 1
    definition_id = definition[0].id

    # a small deterministic market dataset, materialized without any live provider call.
    market_repository = SqlAlchemyMarketDataRepository(database.sessions)
    fake_provider = FakeHistoricalProvider(["100", "101", "99", "102", "102", "98"])
    historical = HistoricalMarketDataService(market_repository, fake_provider, clock)
    datasets = DatasetService(
        market_repository,
        historical,
        clock,
        lease_duration=timedelta(minutes=5),
        max_dataset_candles=1000,
    )
    selection = MarketSelection("BINANCE", "BTCUSDT", Timeframe.ONE_HOUR)
    end = NOW
    start = end - timedelta(hours=6)
    time_range = TimeRange(start, end)
    materialized = await datasets.materialize(selection, time_range, request_id="lifecycle")
    assert materialized.dataset.status is DatasetStatus.COMPLETE
    dataset = materialized.dataset
    dataset_id = dataset.id

    # analyze: the generated strategy resolves and runs through the shared Strategy contract.
    context_reader = SqlAlchemyStrategyContextReader(market_repository)
    analyze = AnalyzeStrategy(definitions, context_reader, registry)
    analysis = await analyze.execute(
        AnalyzeStrategyCommand(
            "lifecycle-analyze", definition_id, str(dataset_id), ContractVersionRange(1, 0, 0)
        )
    )
    assert len(analysis.signals) == 6
    assert {signal.action.value for signal in analysis.signals} == {"HOLD", "BUY", "SELL"}

    # backtest: the same generated strategy, through the ordinary backtest pipeline.
    backtest_repository = SqlAlchemyBacktestRepository(database.sessions)
    policy = ExecutionPolicy(uuid4(), f"lifecycle-next-open-long-only-{uuid4().hex[:8]}", "1.0.0")
    await backtest_repository.ensure_policy(policy, NOW)
    configuration = BacktestConfiguration(
        uuid4(),
        uuid4(),
        dataset_id,
        "1",
        dataset.checksum or "",
        "BINANCE",
        "BTCUSDT",
        Timeframe.ONE_HOUR,
        start,
        end,
        definition_id,
        strategy_id,
        provenance.strategy_version,
        "1.0.0",
        definition[0].parameters.canonical_fingerprint,
        analysis.context_provenance.context_fingerprint,
        policy.id,
        policy.version,
        Decimal("1000"),
        Decimal("0"),
        Decimal("0"),
        42,
    )
    create_run = CreateBacktestRun(backtest_repository, clock)
    run = await create_run.execute(configuration)
    execute_run = ExecuteBacktestRun(
        backtest_repository,
        BacktestDatasetReader(market_repository),
        BacktestStrategyAnalyzer(analyze),
        backtest_repository,
        clock,
    )
    result = await execute_run.execute(run.configuration.run_id, "lifecycle-backtest")
    assert result.configuration.strategy_id == strategy_id
    assert len(result.signals) == 6

    # restart: fresh in-process registry, no LLM/source adapters wired at all. Only
    # this test's own strategy is reloaded; the integration database is shared across
    # test runs and may hold other activated strategies whose artifacts live outside
    # this test's tmp_path.
    reloaded_registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    activated = [
        item
        for item in await generation_repository.list_activated()
        if item.strategy_id == strategy_id
    ]
    assert len(activated) == 1
    for reloaded_provenance in activated:
        reloaded_draft = await generation_repository.get_draft(reloaded_provenance.draft_id)
        reloaded_metadata = await generation_repository.get_artifact(
            reloaded_provenance.artifact_id
        )
        assert reloaded_draft is not None and reloaded_metadata is not None
        stored_artifact = await artifacts.get(reloaded_metadata.content_fingerprint)
        reloaded_registry.register(
            IsolatedGeneratedStrategy(
                strategy_id=reloaded_provenance.strategy_id,
                display_name=reloaded_draft.display_name,
                strategy_version=SemanticVersion.parse(reloaded_provenance.strategy_version),
                parameter_schema=reloaded_draft.parameter_schema,
                artifact=replace(
                    stored_artifact, id=reloaded_metadata.id, draft_id=reloaded_metadata.draft_id
                ),
                runtime=runtime,
                generation_provenance_id=reloaded_provenance.id,
            )
        )

    # reuse: analyze again through the reloaded registry, with model/source adapters gone.
    reloaded_analyze = AnalyzeStrategy(definitions, context_reader, reloaded_registry)
    reused_analysis = await reloaded_analyze.execute(
        AnalyzeStrategyCommand(
            "lifecycle-reuse", definition_id, str(dataset_id), ContractVersionRange(1, 0, 0)
        )
    )
    assert [s.action for s in reused_analysis.signals] == [s.action for s in analysis.signals]

    await database.dispose()
