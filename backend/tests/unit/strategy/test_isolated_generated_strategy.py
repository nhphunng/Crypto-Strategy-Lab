from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from tests.fixtures.strategy.factories import context

from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.generation import GeneratedStrategyArtifact
from crypto_lab.domain.strategy.parameters import (
    ParameterDefinition,
    ParameterSchema,
    ParameterValueType,
)
from crypto_lab.domain.strategy.signal import HistoryState, SignalAction, SignalPhase
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.sandbox.isolated_generated_strategy import (
    IsolatedGeneratedStrategy,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ARTIFACT_ID = UUID(int=4)
PROVENANCE_ID = UUID(int=5)
DEFINITION_ID = UUID(int=7)


class FakeRuntime:
    def __init__(self, respond) -> None:
        self._respond = respond
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def execute(self, source_code: str, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append((source_code, payload))
        return self._respond(payload)


def hold_response(payload: dict[str, object]) -> dict[str, object]:
    return {
        "signals": [
            {"action": "HOLD", "phase": "EVALUATED", "reason": "flat"}
            for _ in payload["context"]["candles"]
        ]
    }


def build_strategy(
    runtime: FakeRuntime,
    *,
    parameter_schema: ParameterSchema = ParameterSchema(()),
    source_code: str = "def analyze(payload):\n    return {'signals': []}\n",
) -> tuple[IsolatedGeneratedStrategy, GeneratedStrategyArtifact]:
    artifact = GeneratedStrategyArtifact.create(
        id=ARTIFACT_ID,
        draft_id=UUID(int=3),
        source_code=source_code,
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    strategy = IsolatedGeneratedStrategy(
        strategy_id="generated-one",
        display_name="Generated One",
        strategy_version=SemanticVersion(1, 0, 0),
        parameter_schema=parameter_schema,
        artifact=artifact,
        runtime=runtime,  # type: ignore[arg-type]
        generation_provenance_id=PROVENANCE_ID,
    )
    return strategy, artifact


def build_definition(
    strategy: IsolatedGeneratedStrategy, artifact: GeneratedStrategyArtifact, raw: dict[str, object]
) -> StrategyDefinition:
    return StrategyDefinition(
        DEFINITION_ID,
        strategy.metadata.strategy_id,
        strategy.metadata.strategy_type,
        strategy.metadata.strategy_version,
        strategy.metadata.contract_version,
        strategy.validate_parameters(raw),
        NOW,
        StrategyOrigin.LLM_GENERATED,
        artifact.id,
        PROVENANCE_ID,
    )


async def test_metadata_reflects_generated_origin_and_artifact_fingerprint() -> None:
    runtime = FakeRuntime(hold_response)
    strategy, artifact = build_strategy(runtime)

    assert strategy.metadata.origin is StrategyOrigin.LLM_GENERATED
    assert strategy.metadata.generation_provenance_id == PROVENANCE_ID
    assert strategy.metadata.generated_artifact_fingerprint == artifact.content_fingerprint
    assert strategy.metadata.strategy_type == "GENERATED"


async def test_validate_parameters_delegates_to_schema() -> None:
    schema = ParameterSchema(
        (ParameterDefinition("period", "lookback", ParameterValueType.INTEGER, 20, 2, 500),)
    )
    runtime = FakeRuntime(hold_response)
    strategy, _ = build_strategy(runtime, parameter_schema=schema)

    validated = strategy.validate_parameters({"period": 30})
    assert validated.values["period"] == 30


async def test_analyze_returns_signals_with_correct_provenance_and_sequence() -> None:
    runtime = FakeRuntime(hold_response)
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100", "101", "102"])

    result = await strategy.analyze(definition, ctx)

    assert len(result.signals) == 3
    assert [signal.sequence for signal in result.signals] == [0, 1, 2]
    assert all(signal.action is SignalAction.HOLD for signal in result.signals)
    assert result.history_state is HistoryState.EVALUABLE
    assert result.context_provenance.dataset_id == ctx.dataset_id
    assert result.context_provenance.context_fingerprint == ctx.context_fingerprint


async def test_analyze_is_deterministic_for_identical_runtime_output() -> None:
    runtime = FakeRuntime(hold_response)
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100", "101"])

    first = await strategy.analyze(definition, ctx)
    second = await strategy.analyze(definition, ctx)

    assert tuple(signal.id for signal in first.signals) == tuple(
        signal.id for signal in second.signals
    )
    assert tuple(s.action for s in first.signals) == tuple(s.action for s in second.signals)


@pytest.mark.parametrize(
    ("raw_signals", "expected_state"),
    [
        ([], HistoryState.EMPTY),
        ([{"action": "HOLD", "phase": "WARMUP"}], HistoryState.INSUFFICIENT),
        ([{"action": "HOLD", "phase": "EVALUATED"}], HistoryState.EVALUABLE),
    ],
)
async def test_analyze_computes_history_state_from_last_signal_phase(
    raw_signals: list[dict[str, object]], expected_state: HistoryState
) -> None:
    closes = ["100"] if raw_signals else []
    runtime = FakeRuntime(lambda payload: {"signals": raw_signals})
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(closes)

    result = await strategy.analyze(definition, ctx)

    assert result.history_state is expected_state
    if raw_signals:
        assert result.signals[-1].phase is SignalPhase.WARMUP or result.signals[
            -1
        ].phase is SignalPhase.EVALUATED


async def test_analyze_sends_canonical_decimal_parameters_and_candle_payload() -> None:
    runtime = FakeRuntime(hold_response)
    schema = ParameterSchema(
        (
            ParameterDefinition(
                "threshold", "cutoff", ParameterValueType.DECIMAL, Decimal("1.50"), None, None
            ),
        )
    )
    strategy, artifact = build_strategy(runtime, parameter_schema=schema)
    definition = build_definition(strategy, artifact, {"threshold": "2.5"})
    ctx = context(["100", "101"])

    await strategy.analyze(definition, ctx)

    assert len(runtime.calls) == 1
    _, payload = runtime.calls[0]
    assert payload["parameters"] == {"threshold": "2.5"}
    assert payload["context"]["datasetId"] == ctx.dataset_id
    candles_payload = payload["context"]["candles"]
    assert isinstance(candles_payload, list)
    assert len(candles_payload) == 2
    assert candles_payload[0]["close"] == "100"


async def test_analyze_rejects_signal_count_mismatch() -> None:
    runtime = FakeRuntime(lambda payload: {"signals": [{"action": "HOLD", "phase": "EVALUATED"}]})
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100", "101"])

    with pytest.raises(ValueError, match="invalid signal count"):
        await strategy.analyze(definition, ctx)


async def test_analyze_rejects_non_list_signals() -> None:
    runtime = FakeRuntime(lambda payload: {"signals": "not-a-list"})
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100"])

    with pytest.raises(ValueError, match="invalid signal count"):
        await strategy.analyze(definition, ctx)


async def test_analyze_rejects_non_dict_signal_item() -> None:
    runtime = FakeRuntime(lambda payload: {"signals": ["not-a-dict"]})
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100"])

    with pytest.raises(ValueError, match="invalid signal"):
        await strategy.analyze(definition, ctx)


async def test_analyze_rejects_invalid_action() -> None:
    bad_signal = {"action": "NOT_REAL", "phase": "EVALUATED"}
    runtime = FakeRuntime(lambda payload: {"signals": [bad_signal]})
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100"])

    with pytest.raises(ValueError):
        await strategy.analyze(definition, ctx)


async def test_analyze_propagates_runtime_failure() -> None:
    def fail(payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("sandbox container exceeded resource limits")

    runtime = FakeRuntime(fail)
    strategy, artifact = build_strategy(runtime)
    definition = build_definition(strategy, artifact, {})
    ctx = context(["100"])

    with pytest.raises(RuntimeError, match="resource limits"):
        await strategy.analyze(definition, ctx)
