import shutil
import subprocess
from datetime import UTC, datetime
from uuid import UUID

import pytest

from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.generation import GeneratedStrategyArtifact
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)
from crypto_lab.infrastructure.sandbox.isolated_generated_strategy import (
    IsolatedGeneratedStrategy,
)
from tests.fixtures.strategy.factories import context


class CapturingRuntime:
    policy_version = DockerGeneratedStrategyRuntime.policy_version

    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def execute(self, source_code: str, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(payload)
        candles = payload["context"]["candles"]
        assert isinstance(candles, list)
        return {
            "signals": [
                {"action": "HOLD", "phase": "EVALUATED", "reason": "fixture"} for _ in candles
            ]
        }


def generated_definition(artifact: GeneratedStrategyArtifact) -> StrategyDefinition:
    return StrategyDefinition(
        id=UUID(int=100),
        strategy_id="market-context-probe",
        strategy_type="GENERATED",
        strategy_version=SemanticVersion(1, 0, 0),
        contract_version=artifact.contract_version,
        parameters=ParameterSchema(()).validate({}),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        origin=StrategyOrigin.LLM_GENERATED,
        generated_artifact_id=artifact.id,
        generation_provenance_id=UUID(int=104),
    )


def generated_artifact(
    source_code: str = "def analyze(payload):\n    return {'signals': []}\n",
) -> GeneratedStrategyArtifact:
    return GeneratedStrategyArtifact.create(
        id=UUID(int=102),
        draft_id=UUID(int=103),
        source_code=source_code,
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pair", "timeframe"),
    (("ETHUSDT", Timeframe.FIVE_MINUTES), ("SOLUSDT", Timeframe.ONE_HOUR)),
)
async def test_generated_strategy_payload_preserves_market_context(
    pair: str,
    timeframe: Timeframe,
) -> None:
    strategy_context: StrategyContext = context(
        ["100.00", "101.2500"],
        pair=pair,
        timeframe=timeframe,
    )
    artifact = generated_artifact()
    runtime = CapturingRuntime()
    strategy = IsolatedGeneratedStrategy(
        strategy_id="market-context-probe",
        display_name="Market Context Probe",
        strategy_version=SemanticVersion(1, 0, 0),
        parameter_schema=ParameterSchema(()),
        artifact=artifact,
        runtime=runtime,  # type: ignore[arg-type]
        generation_provenance_id=UUID(int=104),
    )
    definition = generated_definition(artifact)

    result = await strategy.analyze(definition, strategy_context)

    assert runtime.payloads == [
        {
            "contractVersion": "1.0.0",
            "parameters": {},
            "context": {
                "datasetId": strategy_context.dataset_id,
                "datasetVersion": strategy_context.dataset_version,
                "provider": "BINANCE",
                "pair": pair,
                "timeframe": timeframe.value,
                "rangeStart": format_utc_millis(strategy_context.range_start),
                "rangeEnd": format_utc_millis(strategy_context.range_end),
                "decisionTimestamp": format_utc_millis(strategy_context.decision_timestamp),
                "candles": [
                    {
                        "timestamp": format_utc_millis(candle.open_time),
                        "open": canonical_decimal(candle.open),
                        "high": canonical_decimal(candle.high),
                        "low": canonical_decimal(candle.low),
                        "close": canonical_decimal(candle.close),
                        "volume": canonical_decimal(candle.volume),
                    }
                    for candle in strategy_context.candles
                ],
            },
        }
    ]
    assert result.context_provenance.dataset_id == strategy_context.dataset_id
    assert result.context_provenance.dataset_version == strategy_context.dataset_version
    assert result.context_provenance.context_fingerprint == strategy_context.context_fingerprint
    assert result.context_provenance.provider == strategy_context.provider
    assert result.context_provenance.pair == pair
    assert result.context_provenance.timeframe == timeframe
    assert result.context_provenance.range_start == strategy_context.range_start
    assert result.context_provenance.range_end == strategy_context.range_end
    assert result.context_provenance.decision_timestamp == strategy_context.decision_timestamp
    assert [signal.timestamp for signal in result.signals] == [
        candle.open_time for candle in strategy_context.candles
    ]


@pytest.mark.asyncio
async def test_real_sandbox_executes_generated_code_against_market_context() -> None:
    if not _sandbox_image_available():
        pytest.skip("Docker daemon or sandbox image is unavailable")

    artifact = generated_artifact(
        """
def analyze(payload):
    context = payload["context"]
    label = context["pair"] + "/" + context["timeframe"]
    return {
        "signals": [
            {"action": "HOLD", "phase": "EVALUATED", "reason": label}
            for _ in context["candles"]
        ]
    }
""",
    )
    strategy_context = context(
        ["100.00", "101.2500"],
        pair="ETHUSDT",
        timeframe=Timeframe.FIVE_MINUTES,
    )
    runtime = DockerGeneratedStrategyRuntime()
    strategy = IsolatedGeneratedStrategy(
        strategy_id="market-context-probe",
        display_name="Market Context Probe",
        strategy_version=SemanticVersion(1, 0, 0),
        parameter_schema=ParameterSchema(()),
        artifact=artifact,
        runtime=runtime,  # type: ignore[arg-type]
        generation_provenance_id=UUID(int=104),
    )

    try:
        result = await strategy.analyze(generated_definition(artifact), strategy_context)
    finally:
        await runtime.close()

    assert [signal.reason for signal in result.signals] == ["ETHUSDT/5m", "ETHUSDT/5m"]


def _sandbox_image_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        daemon = subprocess.run(["docker", "info"], capture_output=True, check=False, timeout=5)
        if daemon.returncode != 0:
            return False
        image = subprocess.run(
            ["docker", "image", "inspect", "crypto-lab-strategy-sandbox:1"],
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return daemon.returncode == 0 and image.returncode == 0


def test_sandbox_availability_timeout_is_treated_as_an_environmental_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd="docker", timeout=5)

    monkeypatch.setattr(subprocess, "run", timeout)

    assert _sandbox_image_available() is False
