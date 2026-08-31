from collections.abc import Awaitable
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from crypto_lab.api.dependencies import BALANCED_SCORING_POLICY, EVALUATION_POLICY, Container
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.domain.backtest.configuration import BacktestConfiguration, ExecutionPolicy
from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.evaluation.result import EvaluationResult, create_evaluation_result
from crypto_lab.domain.evaluation.scoring import score_metrics
from crypto_lab.domain.market_data.dataset import calculate_dataset_checksum
from crypto_lab.domain.strategy.context import ContextCompleteness, StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.generation import (
    DraftStatus,
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
)
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.provenance import StrategyGenerationProvenance
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)
from tests.fixtures.strategy.factories import candles, context

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class Repository:
    def __init__(self, provenance, draft, artifact):
        self.provenance, self.draft, self.artifact = provenance, draft, artifact

    async def list_activated(self):
        return (self.provenance,)

    async def get_draft(self, identity):
        return self.draft

    async def get_artifact(self, identity):
        return self.artifact


class Artifacts:
    def __init__(self, artifact):
        self.artifact = artifact

    async def get(self, reference):
        return self.artifact


class Runtime:
    policy_version = DockerGeneratedStrategyRuntime.policy_version

    def __init__(self, actions: tuple[str, ...] | None = None) -> None:
        self.calls = 0
        self.actions = actions

    async def execute(self, source_code, payload):
        self.calls += 1
        actions = self.actions or tuple("HOLD" for _ in payload["context"]["candles"])
        return {
            "signals": [
                {"action": action, "phase": "EVALUATED"} for action in actions
            ]
        }


async def test_activated_strategy_reloads_with_model_and_source_adapters_absent() -> None:
    artifact = GeneratedStrategyArtifact.create(
        id=UUID(int=4),
        draft_id=UUID(int=3),
        source_code="def analyze(payload):\n return {'signals': []}\n",
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    draft = GeneratedStrategyDraft(
        UUID(int=3),
        UUID(int=1),
        UUID(int=2),
        0,
        "persisted-generated",
        "Persisted Generated",
        "Reusable",
        {},
        ParameterSchema(()),
        (),
        (),
        DraftStatus.ACTIVATED,
        artifact.id,
        UUID(int=5),
    )
    provenance = StrategyGenerationProvenance(
        UUID(int=6),
        UUID(int=1),
        UUID(int=2),
        draft.id,
        artifact.id,
        UUID(int=5),
        "persisted-generated",
        "1.0.0",
        "provider",
        "model",
        "1",
        "prompt",
        NOW,
        NOW,
        "analyst",
        "activation-v1",
    )
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    container = Container(
        settings=None,
        clock=None,
        repository=None,
        historical=None,
        datasets=None,  # type: ignore[arg-type]
        strategy_registry=registry,
        strategy_discovery=DiscoverStrategies(registry),
        strategy_generation_repository=Repository(provenance, draft, artifact),  # type: ignore[arg-type]
        generated_artifacts=Artifacts(artifact),  # type: ignore[arg-type]
        generated_runtime=Runtime(),  # type: ignore[arg-type]
    )
    assert container.strategy_generation is None
    await container.load_generated_strategies()
    entry = registry.discover()[0]
    assert entry.strategy_id == "persisted-generated"
    assert entry.metadata.origin.value == "LLM_GENERATED"
    selected = StrategyDefinition(
        UUID(int=7),
        provenance.strategy_id,
        "GENERATED",
        SemanticVersion.parse(provenance.strategy_version),
        SemanticVersion(1, 0, 0),
        draft.parameter_schema.validate({}),
        NOW,
        StrategyOrigin.LLM_GENERATED,
        artifact.id,
        provenance.id,
    )
    strategy = registry.resolve(selected.strategy_id, selected.strategy_version)
    result = await strategy.analyze(selected, context(["100", "101"]))
    assert len(result.signals) == 2
    assert all(signal.action.value == "HOLD" for signal in result.signals)


async def test_reload_fails_closed_when_activated_provenance_is_dangling() -> None:
    artifact = GeneratedStrategyArtifact.create(
        id=UUID(int=4),
        draft_id=UUID(int=3),
        source_code="def analyze(payload):\n return {'signals': []}\n",
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    draft = GeneratedStrategyDraft(
        UUID(int=3),
        UUID(int=1),
        UUID(int=2),
        0,
        "dangling-generated",
        "Dangling Generated",
        "Must not disappear silently",
        {},
        ParameterSchema(()),
        (),
        (),
        DraftStatus.ACTIVATED,
        artifact.id,
        UUID(int=5),
    )
    provenance = StrategyGenerationProvenance(
        UUID(int=6),
        UUID(int=1),
        UUID(int=2),
        draft.id,
        artifact.id,
        UUID(int=5),
        "dangling-generated",
        "1.0.0",
        "provider",
        "model",
        "1",
        "prompt",
        NOW,
        NOW,
        "analyst",
        "activation-v1",
    )
    container = Container(
        settings=None,
        clock=None,
        repository=None,
        historical=None,
        datasets=None,  # type: ignore[arg-type]
        strategy_registry=StrategyRegistry(ContractVersionRange(1, 0, 0)),
        strategy_generation_repository=Repository(provenance, None, None),  # type: ignore[arg-type]
        generated_artifacts=Artifacts(artifact),  # type: ignore[arg-type]
        generated_runtime=Runtime(),  # type: ignore[arg-type]
    )
    with pytest.raises(RuntimeError, match="missing durable references"):
        await container.load_generated_strategies()


async def test_reload_rejects_definition_with_different_generated_provenance() -> None:
    artifact = GeneratedStrategyArtifact.create(
        id=UUID(int=4),
        draft_id=UUID(int=3),
        source_code="def analyze(payload):\n return {'signals': []}\n",
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    draft = GeneratedStrategyDraft(
        UUID(int=3),
        UUID(int=1),
        UUID(int=2),
        0,
        "provenance-guard",
        "Provenance Guard",
        "Must execute only its activated artifact",
        {},
        ParameterSchema(()),
        (),
        (),
        DraftStatus.ACTIVATED,
        artifact.id,
        UUID(int=5),
    )
    provenance = StrategyGenerationProvenance(
        UUID(int=6),
        UUID(int=1),
        UUID(int=2),
        draft.id,
        artifact.id,
        UUID(int=5),
        draft.normalized_name,
        "1.0.0",
        "provider",
        "model",
        "1",
        "prompt",
        NOW,
        NOW,
        "analyst",
        "activation-v1",
    )
    runtime = Runtime()
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    container = Container(
        settings=None,
        clock=None,
        repository=None,
        historical=None,
        datasets=None,  # type: ignore[arg-type]
        strategy_registry=registry,
        strategy_generation_repository=Repository(provenance, draft, artifact),  # type: ignore[arg-type]
        generated_artifacts=Artifacts(artifact),  # type: ignore[arg-type]
        generated_runtime=runtime,  # type: ignore[arg-type]
    )
    await container.load_generated_strategies()
    mismatched = StrategyDefinition(
        UUID(int=7),
        provenance.strategy_id,
        "GENERATED",
        SemanticVersion.parse(provenance.strategy_version),
        artifact.contract_version,
        draft.parameter_schema.validate({}),
        NOW,
        StrategyOrigin.LLM_GENERATED,
        artifact.id,
        UUID(int=99),
    )

    with pytest.raises(StrategyError) as caught:
        await registry.resolve(mismatched.strategy_id, mismatched.strategy_version).analyze(
            mismatched, context(["100", "101"])
        )

    assert caught.value.category is ErrorCategory.INVALID_STRATEGY_METADATA
    assert {issue.field for issue in caught.value.issues} == {"generationProvenanceId"}
    assert runtime.calls == 0


async def test_generated_definition_survives_restart_and_produces_stable_evaluation() -> None:
    dataset_id = UUID("10000000-0000-0000-0000-000000000099")
    definition_id = UUID("20000000-0000-0000-0000-000000000099")
    policy = ExecutionPolicy(
        UUID("30000000-0000-0000-0000-000000000099"),
        "next-open-long-only",
        "1.0.0",
    )
    market = candles(["100", "100", "120", "120"])
    checksum = calculate_dataset_checksum(market)
    strategy_context = StrategyContext(
        str(dataset_id),
        checksum,
        "BINANCE",
        "BTCUSDT",
        market[0].timeframe,
        market[0].open_time,
        market[-1].close_time,
        market[-1].close_time,
        ContextCompleteness.COMPLETE,
        market,
    )
    artifact = GeneratedStrategyArtifact.create(
        id=UUID(int=104),
        draft_id=UUID(int=103),
        source_code="def analyze(payload):\n return {'signals': []}\n",
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    draft = GeneratedStrategyDraft(
        UUID(int=103),
        UUID(int=101),
        UUID(int=102),
        0,
        "generated-lifecycle",
        "Generated Lifecycle",
        "Cross-feature generated strategy",
        {},
        ParameterSchema(()),
        (),
        (),
        DraftStatus.ACTIVATED,
        artifact.id,
        UUID(int=105),
    )
    provenance = StrategyGenerationProvenance(
        UUID(int=106),
        UUID(int=101),
        UUID(int=102),
        draft.id,
        artifact.id,
        UUID(int=105),
        draft.normalized_name,
        "1.0.0",
        "provider",
        "model",
        "1",
        "prompt",
        NOW,
        NOW,
        "analyst",
        "activation-v1",
    )
    definition = StrategyDefinition(
        definition_id,
        provenance.strategy_id,
        "GENERATED",
        SemanticVersion.parse(provenance.strategy_version),
        artifact.contract_version,
        draft.parameter_schema.validate({}),
        NOW,
        StrategyOrigin.LLM_GENERATED,
        artifact.id,
        provenance.id,
    )
    runtime = Runtime(("BUY", "HOLD", "SELL", "HOLD"))

    async def run_after_startup() -> tuple[
        StrategyAnalysisResult, BacktestResult, EvaluationResult
    ]:
        registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
        container = Container(
            settings=None,
            clock=None,
            repository=None,
            historical=None,
            datasets=None,  # type: ignore[arg-type]
            strategy_registry=registry,
            strategy_generation_repository=Repository(provenance, draft, artifact),  # type: ignore[arg-type]
            generated_artifacts=Artifacts(artifact),  # type: ignore[arg-type]
            generated_runtime=runtime,  # type: ignore[arg-type]
        )
        await container.load_generated_strategies()
        selected = registry.resolve(definition.strategy_id, definition.strategy_version)
        analysis = await cast(
            Awaitable[StrategyAnalysisResult], selected.analyze(definition, strategy_context)
        )
        configuration = BacktestConfiguration(
            UUID("40000000-0000-0000-0000-000000000099"),
            UUID("50000000-0000-0000-0000-000000000099"),
            dataset_id,
            "1",
            checksum,
            "BINANCE",
            "BTCUSDT",
            market[0].timeframe,
            market[0].open_time,
            market[-1].close_time,
            definition.id,
            definition.strategy_id,
            str(definition.strategy_version),
            str(definition.contract_version),
            definition.parameters.canonical_fingerprint,
            strategy_context.context_fingerprint,
            policy.id,
            policy.version,
            Decimal("1000"),
            Decimal("0"),
            Decimal("0"),
            42,
        )
        backtest = execute_backtest(configuration, market, analysis, policy, created_at=NOW)
        metrics = calculate_metrics(backtest)
        outcome = score_metrics(metrics, BALANCED_SCORING_POLICY)
        evaluation = create_evaluation_result(
            backtest,
            EVALUATION_POLICY,
            BALANCED_SCORING_POLICY,
            metrics,
            outcome,
            NOW,
        )
        return analysis, backtest, evaluation

    first_analysis, first_backtest, first_evaluation = await run_after_startup()
    restarted_analysis, restarted_backtest, restarted_evaluation = await run_after_startup()

    assert first_analysis.strategy_definition.origin is StrategyOrigin.LLM_GENERATED
    assert first_analysis.strategy_definition.generation_provenance_id == provenance.id
    assert first_analysis.strategy_definition.generated_artifact_id == artifact.id
    assert first_backtest.configuration.strategy_definition_id == definition.id
    assert first_backtest.configuration.strategy_version == provenance.strategy_version
    assert first_backtest.trade_state.value == "HAS_TRADES"
    assert first_backtest.result_checksum == restarted_backtest.result_checksum
    assert first_evaluation.content_fingerprint == restarted_evaluation.content_fingerprint
    assert first_evaluation.metrics == restarted_evaluation.metrics
    assert first_analysis.signals == restarted_analysis.signals
