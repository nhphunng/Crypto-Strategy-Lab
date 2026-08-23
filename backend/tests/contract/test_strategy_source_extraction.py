from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from crypto_lab.application.strategies.generate_strategies import (
    GenerateStrategies,
    GenerateStrategiesCommand,
)
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.domain.strategy.generation import (
    GeneratedStrategyArtifact,
    GenerationSourceType,
    StrategyValidationReport,
    ValidationCheck,
    ValidationStatus,
)
from crypto_lab.domain.strategy.parameters import ParameterSchema


@dataclass
class Candidate:
    normalized_name: str
    display_name: str = "Candidate"
    description: str = "Deterministic rules"
    structured_rules: dict[str, object] = None  # type: ignore[assignment]
    parameter_schema: ParameterSchema = field(default_factory=lambda: ParameterSchema(()))
    assumptions: tuple[str, ...] = ()
    evidence: tuple[object, ...] = ("source",)
    source_code: str = "def analyze(payload):\n return {'signals': []}\n"

    def __post_init__(self):
        self.structured_rules = self.structured_rules or {"entry": "strict crossing"}


class Model:
    provider = "fake"
    model_id = "fake-model"
    model_version = "1"
    prompt_template_version = "fake-prompt-v1"

    def __init__(self, candidates):
        self.candidates = candidates
        self.calls = 0

    async def generate(self, source_type, inert_content, request_id):
        self.calls += 1
        return self.candidates


class Repository:
    def __init__(self):
        self.requests = {}
        self.sources = {}
        self.drafts = {}
        self.artifacts = {}
        self.reports = {}

    async def save_request(self, value):
        self.requests[value.id] = value

    async def save_source(self, value):
        self.sources[value.id] = value

    async def save_draft(self, value):
        self.drafts[value.id] = value
        return value

    async def save_artifact(self, value, reference):
        self.artifacts[value.id] = value
        return value

    async def save_report(self, value):
        self.reports[value.id] = value

    async def get_request(self, identity):
        return self.requests.get(identity)

    async def list_drafts(self, request_id):
        return tuple(
            sorted(
                (
                    draft
                    for draft in self.drafts.values()
                    if draft.generation_request_id == request_id
                ),
                key=lambda draft: draft.candidate_index,
            )
        )

    async def find_report(self, artifact_id, policy_version):
        return next(
            (
                report
                for report in self.reports.values()
                if report.artifact_id == artifact_id and report.policy_version == policy_version
            ),
            None,
        )


class Artifacts:
    def __init__(self, fail_first=False):
        self.fail_first = fail_first
        self.calls = 0

    async def put(self, artifact):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise OSError("artifact store unavailable")
        return artifact.content_fingerprint


class Validator:
    policy_version = "generated-strategy-validation-v1"

    async def validate(self, artifact: GeneratedStrategyArtifact):
        now = datetime(2026, 1, 1, tzinfo=UTC)
        return StrategyValidationReport(
            uuid4(),
            artifact.id,
            artifact.content_fingerprint,
            self.policy_version,
            ValidationStatus.PASSED,
            (ValidationCheck("contract", True, "passed"),),
            (),
            now,
            now,
            "e" * 64,
        )


class Sources:
    async def prepare(self, url, request_id):
        raise AssertionError("not used")


class Clock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=UTC)


async def test_natural_language_produces_zero_to_many_independent_drafts() -> None:
    repository = Repository()
    use_case = GenerateStrategies(
        Model((Candidate("one"), Candidate("two"))),
        Sources(),
        Artifacts(),
        Validator(),
        repository,
        Clock(),
    )  # type: ignore[arg-type]
    request, drafts = await use_case.execute(
        GenerateStrategiesCommand(
            GenerationSourceType.NATURAL_LANGUAGE, "two strategies", UUID(int=1)
        )
    )
    assert request.status.value == "COMPLETED"
    assert [draft.candidate_index for draft in drafts] == [0, 1]
    assert all(draft.status.value == "READY_FOR_CONFIRMATION" for draft in drafts)


async def test_name_mode_rejects_ambiguous_multiple_candidates() -> None:
    repository = Repository()
    use_case = GenerateStrategies(
        Model((Candidate("one"), Candidate("two"))),
        Sources(),
        Artifacts(),
        Validator(),
        repository,
        Clock(),
    )  # type: ignore[arg-type]
    with pytest.raises(StrategyError) as caught:
        await use_case.execute(
            GenerateStrategiesCommand(GenerationSourceType.STRATEGY_NAME, "breakout", UUID(int=2))
        )
    assert caught.value.category is ErrorCategory.STRATEGY_INTENT_UNRESOLVED
    assert repository.requests[UUID(int=2)].status.value == "FAILED"


async def test_name_mode_rejects_an_unresolved_zero_candidate_result() -> None:
    repository = Repository()
    use_case = GenerateStrategies(
        Model(()), Sources(), Artifacts(), Validator(), repository, Clock()
    )  # type: ignore[arg-type]
    with pytest.raises(StrategyError) as caught:
        await use_case.execute(
            GenerateStrategiesCommand(GenerationSourceType.STRATEGY_NAME, "unknown", UUID(int=3))
        )
    assert caught.value.category is ErrorCategory.STRATEGY_INTENT_UNRESOLVED


async def test_completed_request_retry_reuses_the_same_drafts_without_model_reentry() -> None:
    repository = Repository()
    model = Model((Candidate("one"),))
    use_case = GenerateStrategies(model, Sources(), Artifacts(), Validator(), repository, Clock())  # type: ignore[arg-type]
    command = GenerateStrategiesCommand(
        GenerationSourceType.NATURAL_LANGUAGE, "one strategy", UUID(int=4)
    )
    first_request, first_drafts = await use_case.execute(command)
    second_request, second_drafts = await use_case.execute(command)
    assert second_request == first_request
    assert second_drafts == first_drafts
    assert model.calls == 1


async def test_validation_runtime_failure_is_isolated_from_a_passing_sibling() -> None:
    class MixedValidator(Validator):
        calls = 0

        async def validate(self, artifact):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("sandbox unavailable")
            return await super().validate(artifact)

    repository = Repository()
    use_case = GenerateStrategies(
        Model((Candidate("one"), Candidate("two"))),
        Sources(),
        Artifacts(),
        MixedValidator(),
        repository,
        Clock(),
    )  # type: ignore[arg-type]
    request, drafts = await use_case.execute(
        GenerateStrategiesCommand(
            GenerationSourceType.NATURAL_LANGUAGE, "two strategies", UUID(int=5)
        )
    )
    assert request.status.value == "COMPLETED"
    assert [draft.status.value for draft in drafts] == [
        "VALIDATION_FAILED",
        "READY_FOR_CONFIRMATION",
    ]
    assert drafts[0].failure_issues[0].code == "CANDIDATE_PROCESSING_FAILED"


async def test_artifact_store_failure_is_isolated_from_a_passing_sibling() -> None:
    repository = Repository()
    use_case = GenerateStrategies(
        Model((Candidate("one"), Candidate("two"))),
        Sources(),
        Artifacts(fail_first=True),
        Validator(),
        repository,
        Clock(),
    )  # type: ignore[arg-type]
    request, drafts = await use_case.execute(
        GenerateStrategiesCommand(
            GenerationSourceType.NATURAL_LANGUAGE, "two strategies", UUID(int=6)
        )
    )
    assert request.status.value == "COMPLETED"
    assert [draft.status.value for draft in drafts] == [
        "VALIDATION_FAILED",
        "READY_FOR_CONFIRMATION",
    ]
    assert drafts[0].failure_issues[0].code == "CANDIDATE_PROCESSING_FAILED"
