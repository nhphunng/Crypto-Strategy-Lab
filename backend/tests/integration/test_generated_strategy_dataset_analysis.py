import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from crypto_lab.application.market_data.ports import CandlePage
from crypto_lab.application.strategies.analyze_strategy import (
    AnalyzeStrategy,
    AnalyzeStrategyCommand,
)
from crypto_lab.domain.market_data.dataset import (
    CandleDataset,
    DatasetStatus,
    calculate_dataset_checksum,
)
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.generation import GeneratedStrategyArtifact
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion
from crypto_lab.infrastructure.persistence.strategy_context_reader import (
    SqlAlchemyStrategyContextReader,
)
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)
from crypto_lab.infrastructure.sandbox.isolated_generated_strategy import (
    IsolatedGeneratedStrategy,
)
from tests.fixtures.strategy.factories import candles

NOW = datetime(2026, 1, 1, tzinfo=UTC)
DATASET_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ARTIFACT_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
PROVENANCE_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


class MaterializedDatasetRepository:
    def __init__(self, dataset: CandleDataset, values) -> None:
        self.dataset = dataset
        self.values = tuple(values)

    async def get_dataset(self, dataset_id: UUID) -> CandleDataset | None:
        return self.dataset if dataset_id == self.dataset.id else None

    async def list_dataset_candles(
        self,
        dataset_id: UUID,
        cursor: str | None,
        page_size: int,
    ) -> CandlePage:
        assert dataset_id == self.dataset.id
        assert cursor is None
        return CandlePage(self.values[:page_size], None, False)


class CapturingRuntime:
    policy_version = DockerGeneratedStrategyRuntime.policy_version

    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    async def execute(self, source_code: str, payload: dict[str, object]) -> dict[str, object]:
        self.payloads.append(payload)
        context_payload = payload["context"]
        assert isinstance(context_payload, dict)
        context_candles = context_payload["candles"]
        assert isinstance(context_candles, list)
        return {
            "signals": [
                {"action": "HOLD", "phase": "EVALUATED", "reason": "dataset fixture"}
                for _ in context_candles
            ]
        }


class Definitions:
    def __init__(self, value: StrategyDefinition) -> None:
        self.value = value

    async def get(self, identity: UUID) -> StrategyDefinition | None:
        return self.value if identity == self.value.id else None


class Resolver:
    def __init__(self, value: IsolatedGeneratedStrategy) -> None:
        self.value = value

    def resolve(self, strategy_id: str, version: SemanticVersion) -> IsolatedGeneratedStrategy:
        assert strategy_id == self.value.metadata.strategy_id
        assert version == self.value.metadata.strategy_version
        return self.value


def generated_artifact(
    source_code: str = "def analyze(payload):\n    return {'signals': []}\n",
) -> GeneratedStrategyArtifact:
    return GeneratedStrategyArtifact.create(
        id=ARTIFACT_ID,
        draft_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        source_code=source_code,
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )


def build_definition(artifact: GeneratedStrategyArtifact) -> StrategyDefinition:
    return StrategyDefinition(
        id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        strategy_id="dataset-context-probe",
        strategy_type="GENERATED",
        strategy_version=SemanticVersion(1, 0, 0),
        contract_version=artifact.contract_version,
        parameters=ParameterSchema(()).validate({}),
        created_at=NOW,
        origin=StrategyOrigin.LLM_GENERATED,
        generated_artifact_id=artifact.id,
        generation_provenance_id=PROVENANCE_ID,
    )


def build_dataset(pair: str, timeframe: Timeframe, values):
    selected_candles = tuple(values)
    selection = selected_candles[0].selection
    assert selection.pair == pair
    assert selection.timeframe == timeframe
    time_range = TimeRange(selected_candles[0].open_time, selected_candles[-1].close_time)
    return CandleDataset(
        id=DATASET_ID,
        schema_version="1",
        selection=selection,
        time_range=time_range,
        status=DatasetStatus.COMPLETE,
        candle_count=len(selected_candles),
        checksum=calculate_dataset_checksum(selected_candles),
        failure_code=None,
        created_at=NOW,
        updated_at=NOW,
        completed_at=NOW,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pair", "timeframe"),
    (("ETHUSDT", Timeframe.FIVE_MINUTES), ("SOLUSDT", Timeframe.ONE_HOUR)),
)
async def test_materialized_dataset_context_reaches_generated_analysis(
    pair: str,
    timeframe: Timeframe,
) -> None:
    dataset_candles = candles(
        ["100", "101", "102"],
        pair=pair,
        timeframe=timeframe,
    )
    dataset = build_dataset(pair, timeframe, dataset_candles)
    repository = MaterializedDatasetRepository(dataset, dataset_candles)
    reader = SqlAlchemyStrategyContextReader(repository)  # type: ignore[arg-type]
    artifact = generated_artifact()
    definition = build_definition(artifact)
    runtime = CapturingRuntime()
    strategy = IsolatedGeneratedStrategy(
        strategy_id=definition.strategy_id,
        display_name="Dataset Context Probe",
        strategy_version=definition.strategy_version,
        parameter_schema=ParameterSchema(()),
        artifact=artifact,
        runtime=runtime,  # type: ignore[arg-type]
        generation_provenance_id=PROVENANCE_ID,
    )
    use_case = AnalyzeStrategy(Definitions(definition), reader, Resolver(strategy))  # type: ignore[arg-type]

    result = await use_case.execute(
        AnalyzeStrategyCommand(
            request_id="dataset-context-request",
            definition_id=definition.id,
            dataset_id=str(DATASET_ID),
            supported_contract=ContractVersionRange(1, 0, 0),
        )
    )

    context_payload = runtime.payloads[0]["context"]
    assert isinstance(context_payload, dict)
    assert context_payload["datasetId"] == str(DATASET_ID)
    assert context_payload["datasetVersion"] == dataset.checksum
    assert context_payload["provider"] == "BINANCE"
    assert context_payload["pair"] == pair
    assert context_payload["timeframe"] == timeframe.value
    assert context_payload["rangeStart"] == "2026-01-01T00:00:00.000Z"
    assert context_payload["rangeEnd"] == (
        "2026-01-01T00:14:59.999Z"
        if timeframe is Timeframe.FIVE_MINUTES
        else "2026-01-01T02:59:59.999Z"
    )
    assert len(context_payload["candles"]) == len(dataset_candles)
    assert [item["close"] for item in context_payload["candles"]] == ["100", "101", "102"]
    assert result.context_provenance.dataset_id == str(DATASET_ID)
    assert result.context_provenance.dataset_version == dataset.checksum
    assert result.context_provenance.provider == "BINANCE"
    assert result.context_provenance.pair == pair
    assert result.context_provenance.timeframe is timeframe
    assert [signal.timestamp for signal in result.signals] == [
        item.open_time for item in dataset_candles
    ]


@pytest.mark.asyncio
async def test_materialized_dataset_rejects_mismatched_candle_selection_before_runtime() -> None:
    dataset_candles = candles(
        ["100", "101"],
        pair="SOLUSDT",
        timeframe=Timeframe.ONE_HOUR,
    )
    mismatched_candles = candles(
        ["100", "101"],
        pair="ETHUSDT",
        timeframe=Timeframe.ONE_HOUR,
    )
    dataset = build_dataset("SOLUSDT", Timeframe.ONE_HOUR, dataset_candles)
    reader = SqlAlchemyStrategyContextReader(
        MaterializedDatasetRepository(dataset, mismatched_candles)  # type: ignore[arg-type]
    )

    with pytest.raises(StrategyError) as raised:
        await reader.get_strategy_context(str(DATASET_ID))

    assert raised.value.category is ErrorCategory.INVALID_CONTEXT


@pytest.mark.asyncio
async def test_materialized_dataset_reaches_the_real_sandbox_through_analyze_strategy() -> None:
    if not _sandbox_image_available():
        pytest.skip("Docker daemon or sandbox image is unavailable")

    dataset_candles = candles(
        ["200", "201", "202"],
        pair="SOLUSDT",
        timeframe=Timeframe.ONE_HOUR,
    )
    dataset = build_dataset("SOLUSDT", Timeframe.ONE_HOUR, dataset_candles)
    reader = SqlAlchemyStrategyContextReader(
        MaterializedDatasetRepository(dataset, dataset_candles)  # type: ignore[arg-type]
    )
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
    definition = build_definition(artifact)
    runtime = DockerGeneratedStrategyRuntime()
    strategy = IsolatedGeneratedStrategy(
        strategy_id=definition.strategy_id,
        display_name="Dataset Context Probe",
        strategy_version=definition.strategy_version,
        parameter_schema=ParameterSchema(()),
        artifact=artifact,
        runtime=runtime,  # type: ignore[arg-type]
        generation_provenance_id=PROVENANCE_ID,
    )
    use_case = AnalyzeStrategy(Definitions(definition), reader, Resolver(strategy))  # type: ignore[arg-type]

    try:
        result = await use_case.execute(
            AnalyzeStrategyCommand(
                request_id="real-sandbox-dataset-context-request",
                definition_id=definition.id,
                dataset_id=str(DATASET_ID),
                supported_contract=ContractVersionRange(1, 0, 0),
            )
        )
    finally:
        await runtime.close()

    assert [signal.reason for signal in result.signals] == ["SOLUSDT/1h"] * 3
    assert result.context_provenance.dataset_id == str(DATASET_ID)
    assert result.context_provenance.dataset_version == dataset.checksum
    assert result.context_provenance.pair == "SOLUSDT"
    assert result.context_provenance.timeframe is Timeframe.ONE_HOUR


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pair", "timeframe"),
    (("ETHUSDT", Timeframe.FIVE_MINUTES), ("SOLUSDT", Timeframe.ONE_HOUR)),
)
async def test_postgres_materialized_dataset_reconstructs_strategy_context(
    postgres_repository,
    pair: str,
    timeframe: Timeframe,
) -> None:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    time_range = TimeRange(start, start + timeframe.duration * 3)
    dataset_candles = candles(
        ["100", "101", "102"],
        pair=pair,
        timeframe=timeframe,
        start=start,
    )

    claim = await postgres_repository.claim_dataset(
        dataset_candles[0].selection,
        time_range,
        start + timedelta(days=1),
        timedelta(minutes=5),
    )
    assert claim.acquired is True
    assert claim.build_token is not None

    await postgres_repository.store_closed_candles(dataset_candles)
    completed = await postgres_repository.finalize_dataset(
        claim.dataset.id,
        claim.build_token,
        dataset_candles,
        start + timedelta(days=1),
    )

    reader = SqlAlchemyStrategyContextReader(postgres_repository)
    context = await reader.get_strategy_context(str(completed.id))

    assert context is not None
    assert context.dataset_id == str(completed.id)
    assert context.dataset_version == completed.checksum
    assert context.provider == "BINANCE"
    assert context.pair == pair
    assert context.timeframe is timeframe
    assert context.range_start == time_range.start_time
    assert context.range_end == time_range.end_time
    assert context.candles == dataset_candles


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
    return image.returncode == 0
