from datetime import UTC, datetime
from uuid import UUID

from crypto_lab.api.dependencies import Container
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.generation import (
    DraftStatus,
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
)
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.provenance import StrategyGenerationProvenance
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)
from tests.fixtures.strategy.factories import context

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

    async def execute(self, source_code, payload):
        return {
            "signals": [
                {"action": "HOLD", "phase": "EVALUATED"} for _ in payload["context"]["candles"]
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
