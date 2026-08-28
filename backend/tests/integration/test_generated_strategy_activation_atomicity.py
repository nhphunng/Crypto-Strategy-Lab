"""Real-Postgres proof that activation cannot leave a strategy ACTIVATED without
its definition (or a definition without an activated provenance record).

See docs/ADR for the activation-consistency decision this test guards.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.generation import (
    DraftStatus,
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
    GenerationRequestStatus,
    GenerationSourceType,
    StrategyGenerationRequest,
    StrategyValidationReport,
    ValidationCheck,
    ValidationStatus,
)
from crypto_lab.domain.strategy.parameters import ParameterSchema
from crypto_lab.domain.strategy.provenance import (
    RetentionClass,
    StrategyGenerationProvenance,
    StrategySourceSnapshot,
)
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.repositories.strategy_generation_repository import (
    SqlAlchemyStrategyGenerationRepository,
)
from crypto_lab.infrastructure.persistence.strategy_generation_models import (
    GeneratedStrategyDraftRow,
    StrategyGenerationProvenanceRow,
)
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow
from crypto_lab.infrastructure.security.source_content_protector import (
    LocalAesKeyProvider,
    SourceContentProtector,
)
from tests.conftest import TEST_DATABASE_URL

NOW = datetime(2026, 1, 1, tzinfo=UTC)


async def _seed_ready_draft(
    repository: SqlAlchemyStrategyGenerationRepository,
) -> tuple[GeneratedStrategyDraft, GeneratedStrategyArtifact, StrategyValidationReport]:
    request = StrategyGenerationRequest(
        uuid4(),
        GenerationSourceType.STRATEGY_NAME,
        "atomicity-fixture",
        GenerationRequestStatus.COMPLETED,
        NOW,
        NOW,
    )
    await repository.save_request(request)
    source = StrategySourceSnapshot(
        uuid4(),
        GenerationSourceType.STRATEGY_NAME,
        hashlib.sha256(uuid4().bytes).hexdigest(),
        "source-access-v1",
        RetentionClass.FINGERPRINT_ONLY,
    )
    await repository.save_source(source)
    draft = GeneratedStrategyDraft(
        uuid4(),
        request.id,
        source.id,
        0,
        "atomicity-strategy-" + uuid4().hex[:8],
        "Atomicity Strategy",
        "Fixture for activation atomicity tests",
        {"entry": "close > high"},
        ParameterSchema(()),
        (),
        (),
        DraftStatus.NEEDS_REVIEW,
    )
    saved_draft = await repository.save_draft(draft)
    artifact = GeneratedStrategyArtifact.create(
        id=uuid4(),
        draft_id=saved_draft.id,
        source_code=f"def analyze(payload):\n    return {{'signals': []}}  # {uuid4().hex}\n",
        contract_version=SemanticVersion(1, 0, 0),
        declared_imports=frozenset(),
        capabilities=frozenset(),
        created_at=NOW,
    )
    stored_artifact = await repository.save_artifact(artifact, artifact.content_fingerprint)
    report = StrategyValidationReport(
        uuid4(),
        stored_artifact.id,
        stored_artifact.content_fingerprint,
        "generated-strategy-activation-v1",
        ValidationStatus.PASSED,
        (ValidationCheck("contract", True, "passed"),),
        (),
        NOW,
        NOW,
        "e" * 64,
    )
    await repository.save_report(report)
    ready_draft = GeneratedStrategyDraft(
        saved_draft.id,
        saved_draft.generation_request_id,
        saved_draft.source_snapshot_id,
        saved_draft.candidate_index,
        saved_draft.normalized_name,
        saved_draft.display_name,
        saved_draft.description,
        saved_draft.structured_rules,
        saved_draft.parameter_schema,
        saved_draft.assumptions,
        saved_draft.evidence,
        DraftStatus.READY_FOR_CONFIRMATION,
        stored_artifact.id,
        report.id,
    )
    await repository.save_draft(ready_draft)
    return ready_draft, stored_artifact, report


@pytest.mark.integration
async def test_activation_with_invalid_definition_reference_rolls_back_provenance_too() -> None:
    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    protector = SourceContentProtector(LocalAesKeyProvider(os.urandom(32), "test-activation-key"))
    repository = SqlAlchemyStrategyGenerationRepository(database.sessions, protector)
    draft, artifact, report = await _seed_ready_draft(repository)

    provenance = StrategyGenerationProvenance(
        uuid4(),
        draft.generation_request_id,
        draft.source_snapshot_id,
        draft.id,
        artifact.id,
        report.id,
        draft.normalized_name,
        "1.0.0",
        "provider",
        "model",
        "1",
        "prompt-v1",
        artifact.created_at,
        NOW,
        "analyst",
        "generated-strategy-activation-v1",
    )
    # A generated_artifact_id that references no real artifact row: the definition
    # insert must fail on its foreign key, and that failure must roll back the
    # provenance row and the draft-status flip inserted earlier in the same call.
    bogus_definition = StrategyDefinition(
        uuid4(),
        draft.normalized_name,
        "GENERATED",
        SemanticVersion(1, 0, 0),
        artifact.contract_version,
        draft.parameter_schema.validate({}),
        NOW,
        StrategyOrigin.LLM_GENERATED,
        UUID(int=999_999_999),
        provenance.id,
    )

    with pytest.raises(Exception):  # noqa: B017 - any DB integrity error is acceptable here
        await repository.activate(draft, provenance, bogus_definition)

    async with database.sessions() as session:
        draft_row = await session.get(GeneratedStrategyDraftRow, draft.id)
        assert draft_row is not None
        assert draft_row.status == DraftStatus.READY_FOR_CONFIRMATION.value

        provenance_row = await session.get(StrategyGenerationProvenanceRow, provenance.id)
        assert provenance_row is None

        definition_row = await session.get(StrategyDefinitionRow, bogus_definition.id)
        assert definition_row is None

    await database.dispose()


@pytest.mark.integration
async def test_successful_activation_persists_provenance_and_definition_together() -> None:
    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    protector = SourceContentProtector(LocalAesKeyProvider(os.urandom(32), "test-activation-key"))
    repository = SqlAlchemyStrategyGenerationRepository(database.sessions, protector)
    draft, artifact, report = await _seed_ready_draft(repository)

    provenance = StrategyGenerationProvenance(
        uuid4(),
        draft.generation_request_id,
        draft.source_snapshot_id,
        draft.id,
        artifact.id,
        report.id,
        draft.normalized_name,
        "1.0.0",
        "provider",
        "model",
        "1",
        "prompt-v1",
        artifact.created_at,
        NOW,
        "analyst",
        "generated-strategy-activation-v1",
    )
    definition = StrategyDefinition(
        uuid4(),
        draft.normalized_name,
        "GENERATED",
        SemanticVersion(1, 0, 0),
        artifact.contract_version,
        draft.parameter_schema.validate({}),
        NOW,
        StrategyOrigin.LLM_GENERATED,
        artifact.id,
        provenance.id,
    )

    await repository.activate(draft, provenance, definition)

    async with database.sessions() as session:
        draft_row = await session.get(GeneratedStrategyDraftRow, draft.id)
        assert draft_row is not None
        assert draft_row.status == DraftStatus.ACTIVATED.value

        provenance_row = await session.get(StrategyGenerationProvenanceRow, provenance.id)
        assert provenance_row is not None

        definition_row = await session.get(StrategyDefinitionRow, definition.id)
        assert definition_row is not None
        assert definition_row.generation_provenance_id == provenance.id

    await database.dispose()
