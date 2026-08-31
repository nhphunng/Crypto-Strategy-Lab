from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from crypto_lab.application.strategies.activate_generated_strategy import (
    ActivateGeneratedStrategy,
    ActivateGeneratedStrategyCommand,
)
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.generation import (
    DraftStatus,
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
    StrategyValidationReport,
    ValidationCheck,
    ValidationStatus,
)
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.registry import StrategyRegistry
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class Repository:
    def __init__(self, draft, artifact, report):
        self.draft, self.artifact, self.report = draft, artifact, report
        self.activations = []
        self.definitions = []
        self.existing = None

    async def get_draft(self, identity):
        return self.draft if identity == self.draft.id else None

    async def get_artifact(self, identity):
        return self.artifact if identity == self.artifact.id else None

    async def get_report(self, identity):
        return self.report if identity == self.report.id else None

    async def activate(self, draft, provenance, definition=None):
        self.activations.append(provenance)
        self.definitions.append(definition)
        self.draft = replace(draft, status=DraftStatus.ACTIVATED)

    async def find_activated_by_content(self, strategy_id, artifact_fingerprint):
        return self.existing


class Definitions:
    def __init__(self):
        self.values = []

    async def create_or_resolve(self, definition):
        self.values.append(definition)
        return definition


class Artifacts:
    def __init__(self, value):
        self.value = value

    async def get(self, reference):
        assert reference == self.value.content_fingerprint
        return self.value


class Model:
    provider = "fake"
    model_id = "model"
    model_version = "1"
    prompt_template_version = "prompt-v1"


class Clock:
    def now(self):
        return NOW


def fixture():
    draft = GeneratedStrategyDraft(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        0,
        "generated-breakout",
        "Generated Breakout",
        "Strict breakout",
        {"entry": "close > high"},
        ParameterSchema(()),
        (),
        (),
        DraftStatus.READY_FOR_CONFIRMATION,
        UUID(int=4),
        UUID(int=5),
    )
    artifact = GeneratedStrategyArtifact.create(
        id=UUID(int=4),
        draft_id=draft.id,
        source_code="def analyze(payload):\n return {'signals': []}\n",
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    report = StrategyValidationReport(
        UUID(int=5),
        artifact.id,
        artifact.content_fingerprint,
        DockerGeneratedStrategyRuntime.policy_version,
        ValidationStatus.PASSED,
        (ValidationCheck("contract", True, "passed"),),
        (),
        NOW,
        NOW,
        "e" * 64,
    )
    return draft, artifact, report


async def test_activation_requires_confirmation_and_exact_reviewed_fingerprints() -> None:
    draft, artifact, report = fixture()
    repository = Repository(draft, artifact, report)
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    use_case = ActivateGeneratedStrategy(
        repository,
        Artifacts(artifact),
        registry,
        DockerGeneratedStrategyRuntime(),
        Model(),
        Clock(),
    )  # type: ignore[arg-type]
    with pytest.raises(StrategyError) as caught:
        await use_case.execute(
            ActivateGeneratedStrategyCommand(
                draft.id, draft.draft_fingerprint, artifact.content_fingerprint, report.id, False
            )
        )
    assert caught.value.category is ErrorCategory.ACTIVATION_NOT_ALLOWED
    assert registry.discover() == ()


async def test_passing_confirmed_draft_is_atomically_published_for_reuse() -> None:
    draft, artifact, report = fixture()
    repository = Repository(draft, artifact, report)
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    use_case = ActivateGeneratedStrategy(
        repository,
        Artifacts(artifact),
        registry,
        DockerGeneratedStrategyRuntime(),
        Model(),
        Clock(),
    )  # type: ignore[arg-type]
    provenance = await use_case.execute(
        ActivateGeneratedStrategyCommand(
            draft.id, draft.draft_fingerprint, artifact.content_fingerprint, report.id, True
        )
    )
    assert provenance.strategy_id == "generated-breakout"
    assert registry.discover()[0].metadata.origin.value == "LLM_GENERATED"
    assert repository.draft.status is DraftStatus.ACTIVATED


async def test_activation_persists_a_default_generated_strategy_definition() -> None:
    draft, artifact, report = fixture()
    repository = Repository(draft, artifact, report)
    definitions = Definitions()
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    use_case = ActivateGeneratedStrategy(
        repository,
        Artifacts(artifact),
        registry,
        DockerGeneratedStrategyRuntime(),
        Model(),
        Clock(),
        definitions,
    )  # type: ignore[arg-type]
    provenance = await use_case.execute(
        ActivateGeneratedStrategyCommand(
            draft.id, draft.draft_fingerprint, artifact.content_fingerprint, report.id, True
        )
    )
    definition = repository.definitions[-1]
    assert definition.strategy_id == provenance.strategy_id
    assert definition.generation_provenance_id == provenance.id
    assert definition.generated_artifact_id == artifact.id


async def test_activation_uses_database_identity_when_content_store_reuses_source() -> None:
    draft, artifact, report = fixture()
    stored_copy = replace(artifact, id=UUID(int=99), draft_id=UUID(int=98))
    repository = Repository(draft, artifact, report)
    definitions = Definitions()
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    use_case = ActivateGeneratedStrategy(
        repository,
        Artifacts(stored_copy),
        registry,
        DockerGeneratedStrategyRuntime(),
        Model(),
        Clock(),
        definitions,
    )  # type: ignore[arg-type]

    provenance = await use_case.execute(
        ActivateGeneratedStrategyCommand(
            draft.id, draft.draft_fingerprint, artifact.content_fingerprint, report.id, True
        )
    )

    assert provenance.artifact_id == artifact.id
    assert repository.definitions[-1].generated_artifact_id == artifact.id


async def test_duplicate_content_activation_links_the_new_draft_to_existing_version() -> None:
    draft, artifact, report = fixture()
    repository = Repository(draft, artifact, report)
    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    first = ActivateGeneratedStrategy(
        repository,
        Artifacts(artifact),
        registry,
        DockerGeneratedStrategyRuntime(),
        Model(),
        Clock(),
    )  # type: ignore[arg-type]
    existing = await first.execute(
        ActivateGeneratedStrategyCommand(
            draft.id, draft.draft_fingerprint, artifact.content_fingerprint, report.id, True
        )
    )
    duplicate = replace(draft, id=UUID(int=11), status=DraftStatus.READY_FOR_CONFIRMATION)
    repository.draft = duplicate
    repository.existing = existing
    linked = await first.execute(
        ActivateGeneratedStrategyCommand(
            duplicate.id,
            duplicate.draft_fingerprint,
            artifact.content_fingerprint,
            report.id,
            True,
        )
    )
    assert linked.id != existing.id
    assert linked.strategy_version == existing.strategy_version
    assert linked.draft_id == duplicate.id
    assert repository.draft.status is DraftStatus.ACTIVATED
    assert len(registry.discover()) == 1
