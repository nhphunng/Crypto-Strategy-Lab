from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.market_data.candle import canonical_decimal
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.errors import ErrorIssue
from crypto_lab.domain.strategy.generation import (
    DraftStatus,
    GeneratedStrategyArtifact,
    GeneratedStrategyDraft,
    GenerationRequestStatus,
    GenerationSourceType,
    RuleEvidence,
    StrategyGenerationRequest,
    StrategyValidationReport,
    ValidationCheck,
    ValidationStatus,
)
from crypto_lab.domain.strategy.parameters import (
    ParameterDefinition,
    ParameterSchema,
    ParameterValueType,
    RelationshipRule,
)
from crypto_lab.domain.strategy.provenance import (
    RetentionClass,
    StrategyGenerationProvenance,
    StrategySourceSnapshot,
)
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.persistence.strategy_generation_models import (
    GeneratedStrategyArtifactRow,
    GeneratedStrategyDraftRow,
    StrategyGenerationProvenanceRow,
    StrategyGenerationRequestRow,
    StrategySourceSnapshotRow,
    StrategyValidationReportRow,
)
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow
from crypto_lab.infrastructure.security.source_content_protector import (
    ProtectedSourceContent,
    SourceContentProtector,
)


class SqlAlchemyStrategyGenerationRepository:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        protector: SourceContentProtector,
    ) -> None:
        self._sessions = sessions
        self._protector = protector

    async def save_request(self, request: StrategyGenerationRequest) -> None:
        protected = self._protector.protect(
            request.submitted_value.encode(), source_id=str(request.id)
        )
        values = {
            "id": request.id,
            "source_type": request.source_type.value,
            "protected_submitted_value": protected.envelope,
            "submitted_value_key_id": protected.key_id,
            "submitted_value_expires_at": request.requested_at + timedelta(days=30),
            "submitted_value_purged_at": None,
            "source_snapshot_id": request.source_snapshot_id,
            "status": request.status.value,
            "requested_at": request.requested_at,
            "updated_at": request.updated_at,
        }
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(StrategyGenerationRequestRow)
                .values(values)
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "source_snapshot_id": request.source_snapshot_id,
                        "status": request.status.value,
                        "updated_at": request.updated_at,
                    },
                )
            )

    async def save_source(self, source: StrategySourceSnapshot) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(StrategySourceSnapshotRow)
                .values(**_source_values(source))
                .on_conflict_do_nothing(index_elements=["id"])
            )

    async def save_draft(self, draft: GeneratedStrategyDraft) -> GeneratedStrategyDraft:
        values = _draft_values(draft)
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(GeneratedStrategyDraftRow)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=["generation_request_id", "candidate_index"],
                    set_={
                        "status": draft.status.value,
                        "generated_artifact_id": draft.generated_artifact_id,
                        "validation_report_id": draft.validation_report_id,
                        "failure_issues": [
                            {
                                "field": issue.field,
                                "code": issue.code,
                                "message": issue.message,
                            }
                            for issue in draft.failure_issues
                        ],
                    },
                )
            )
            row = await session.scalar(
                select(GeneratedStrategyDraftRow).where(
                    GeneratedStrategyDraftRow.generation_request_id == draft.generation_request_id,
                    GeneratedStrategyDraftRow.candidate_index == draft.candidate_index,
                )
            )
            if row is None:
                raise RuntimeError("generated draft could not be resolved")
            return _to_draft(row)

    async def save_artifact(
        self, artifact: GeneratedStrategyArtifact, reference: str
    ) -> GeneratedStrategyArtifact:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(GeneratedStrategyArtifactRow)
                .values(
                    id=artifact.id,
                    draft_id=artifact.draft_id,
                    content_reference=reference,
                    content_fingerprint=artifact.content_fingerprint,
                    contract_version=str(artifact.contract_version),
                    declared_imports=sorted(artifact.declared_imports),
                    capabilities=sorted(artifact.capabilities),
                    language=artifact.language,
                    language_version=artifact.language_version,
                    created_at=artifact.created_at,
                )
                .on_conflict_do_nothing(index_elements=["content_fingerprint", "contract_version"])
            )
            row = await session.scalar(
                select(GeneratedStrategyArtifactRow).where(
                    GeneratedStrategyArtifactRow.content_fingerprint
                    == artifact.content_fingerprint,
                    GeneratedStrategyArtifactRow.contract_version == str(artifact.contract_version),
                )
            )
            if row is None:
                raise RuntimeError("generated artifact could not be resolved")
            return GeneratedStrategyArtifact(
                row.id,
                row.draft_id,
                artifact.source_code,
                row.content_fingerprint,
                SemanticVersion.parse(row.contract_version),
                frozenset(row.declared_imports),
                frozenset(row.capabilities),
                row.created_at,
                row.language,
                row.language_version,
            )

    async def save_report(self, report: StrategyValidationReport) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(StrategyValidationReportRow)
                .values(
                    id=report.id,
                    artifact_id=report.artifact_id,
                    artifact_fingerprint=report.artifact_fingerprint,
                    policy_version=report.policy_version,
                    status=report.status.value,
                    checks=[
                        {"name": item.name, "passed": item.passed, "message": item.message}
                        for item in report.checks
                    ],
                    findings=[
                        {"field": item.field, "code": item.code, "message": item.message}
                        for item in report.findings
                    ],
                    started_at=report.started_at,
                    completed_at=report.completed_at,
                    environment_fingerprint=report.environment_fingerprint,
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )

    async def get_request(self, request_id: UUID) -> StrategyGenerationRequest | None:
        async with self._sessions() as session:
            row = await session.get(StrategyGenerationRequestRow, request_id)
        if row is None:
            return None
        if row.protected_submitted_value is None or row.submitted_value_key_id is None:
            submitted = "[PURGED]"
        else:
            submitted = self._protector.reveal(
                ProtectedSourceContent(row.protected_submitted_value, row.submitted_value_key_id),
                source_id=str(row.id),
            ).decode()
        return StrategyGenerationRequest(
            row.id,
            GenerationSourceType(row.source_type),
            submitted,
            GenerationRequestStatus(row.status),
            row.requested_at,
            row.updated_at,
            row.source_snapshot_id,
        )

    async def get_draft(self, draft_id: UUID) -> GeneratedStrategyDraft | None:
        async with self._sessions() as session:
            row = await session.get(GeneratedStrategyDraftRow, draft_id)
        return None if row is None else _to_draft(row)

    async def list_drafts(self, request_id: UUID) -> tuple[GeneratedStrategyDraft, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(GeneratedStrategyDraftRow)
                    .where(GeneratedStrategyDraftRow.generation_request_id == request_id)
                    .order_by(GeneratedStrategyDraftRow.candidate_index)
                )
            ).all()
        return tuple(_to_draft(row) for row in rows)

    async def get_source(self, source_id: UUID) -> StrategySourceSnapshot | None:
        async with self._sessions() as session:
            row = await session.get(StrategySourceSnapshotRow, source_id)
        if row is None:
            return None
        return StrategySourceSnapshot(
            id=row.id,
            source_type=GenerationSourceType(row.source_type),
            submitted_url=row.submitted_url,
            canonical_url=row.canonical_url,
            title=row.title,
            attribution=row.attribution,
            retrieved_at=row.retrieved_at,
            content_fingerprint=row.content_fingerprint,
            encrypted_content=row.encrypted_content,
            encryption_key_id=row.encryption_key_id,
            media_type=row.media_type,
            size=row.size,
            access_policy_version=row.access_policy_version,
            retention_class=RetentionClass(row.retention_class),
            raw_content_expires_at=row.raw_content_expires_at,
            raw_content_purged_at=row.raw_content_purged_at,
        )

    async def get_artifact(self, artifact_id: UUID) -> GeneratedStrategyArtifact | None:
        async with self._sessions() as session:
            row = await session.get(GeneratedStrategyArtifactRow, artifact_id)
        if row is None:
            return None
        return GeneratedStrategyArtifact(
            row.id,
            row.draft_id,
            "",
            row.content_fingerprint,
            SemanticVersion.parse(row.contract_version),
            frozenset(row.declared_imports),
            frozenset(row.capabilities),
            row.created_at,
            row.language,
            row.language_version,
        )

    async def get_report(self, report_id: UUID) -> StrategyValidationReport | None:
        async with self._sessions() as session:
            row = await session.get(StrategyValidationReportRow, report_id)
        if row is None:
            return None
        return StrategyValidationReport(
            row.id,
            row.artifact_id,
            row.artifact_fingerprint,
            row.policy_version,
            ValidationStatus(row.status),
            tuple(
                ValidationCheck(str(i["name"]), bool(i["passed"]), str(i["message"]))
                for i in row.checks
            ),
            tuple(
                ErrorIssue(
                    None if i.get("field") is None else str(i["field"]),
                    str(i["code"]),
                    str(i["message"]),
                )
                for i in row.findings
            ),
            row.started_at,
            row.completed_at,
            row.environment_fingerprint,
        )

    async def find_report(
        self, artifact_id: UUID, policy_version: str
    ) -> StrategyValidationReport | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(StrategyValidationReportRow)
                .where(
                    StrategyValidationReportRow.artifact_id == artifact_id,
                    StrategyValidationReportRow.policy_version == policy_version,
                )
                .order_by(StrategyValidationReportRow.completed_at.desc())
                .limit(1)
            )
        if row is None:
            return None
        return StrategyValidationReport(
            row.id,
            row.artifact_id,
            row.artifact_fingerprint,
            row.policy_version,
            ValidationStatus(row.status),
            tuple(
                ValidationCheck(str(i["name"]), bool(i["passed"]), str(i["message"]))
                for i in row.checks
            ),
            tuple(
                ErrorIssue(
                    None if i.get("field") is None else str(i["field"]),
                    str(i["code"]),
                    str(i["message"]),
                )
                for i in row.findings
            ),
            row.started_at,
            row.completed_at,
            row.environment_fingerprint,
        )

    async def activate(
        self,
        draft: GeneratedStrategyDraft,
        provenance: StrategyGenerationProvenance,
        definition: StrategyDefinition | None = None,
    ) -> None:
        async with self._sessions() as session, session.begin():
            row = await session.scalar(
                select(GeneratedStrategyDraftRow)
                .where(GeneratedStrategyDraftRow.id == draft.id)
                .with_for_update()
            )
            if row is None or row.status != DraftStatus.READY_FOR_CONFIRMATION.value:
                raise ValueError("draft is not atomically activatable")
            await session.execute(
                insert(StrategyGenerationProvenanceRow).values(
                    id=provenance.id,
                    request_id=provenance.request_id,
                    source_snapshot_id=provenance.source_snapshot_id,
                    draft_id=provenance.draft_id,
                    artifact_id=provenance.artifact_id,
                    validation_report_id=provenance.validation_report_id,
                    strategy_id=provenance.strategy_id,
                    strategy_version=provenance.strategy_version,
                    model_provider=provenance.model_provider,
                    model_id=provenance.model_id,
                    model_version=provenance.model_version,
                    prompt_template_version=provenance.prompt_template_version,
                    generated_at=provenance.generated_at,
                    confirmed_at=provenance.confirmed_at,
                    confirmed_by=provenance.confirmed_by,
                    activation_policy_version=provenance.activation_policy_version,
                )
            )
            row.status = DraftStatus.ACTIVATED.value
            if definition is not None:
                # Inserted in the same transaction as the provenance row above so a
                # generated strategy can never be left ACTIVATED without its definition,
                # or vice versa: either both commit or the whole activation rolls back.
                values = {
                    key: value if isinstance(value, int) else canonical_decimal(value)
                    for key, value in definition.parameters.values.items()
                }
                await session.execute(
                    insert(StrategyDefinitionRow)
                    .values(
                        id=definition.id,
                        strategy_id=definition.strategy_id,
                        strategy_type=definition.strategy_type,
                        strategy_version=str(definition.strategy_version),
                        contract_version=str(definition.contract_version),
                        parameters=values,
                        parameter_schema_fingerprint=definition.parameters.schema_fingerprint,
                        content_fingerprint=definition.content_fingerprint,
                        created_at=definition.created_at,
                        origin=definition.origin.value,
                        generated_artifact_id=definition.generated_artifact_id,
                        generation_provenance_id=definition.generation_provenance_id,
                    )
                    .on_conflict_do_nothing(index_elements=["content_fingerprint"])
                )

    async def list_activated(self) -> tuple[StrategyGenerationProvenance, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(StrategyGenerationProvenanceRow).order_by(
                        StrategyGenerationProvenanceRow.strategy_id,
                        StrategyGenerationProvenanceRow.strategy_version,
                    )
                )
            ).all()
        return tuple(
            StrategyGenerationProvenance(
                row.id,
                row.request_id,
                row.source_snapshot_id,
                row.draft_id,
                row.artifact_id,
                row.validation_report_id,
                row.strategy_id,
                row.strategy_version,
                row.model_provider,
                row.model_id,
                row.model_version,
                row.prompt_template_version,
                row.generated_at,
                row.confirmed_at,
                row.confirmed_by,
                row.activation_policy_version,
            )
            for row in rows
        )

    async def find_activated_by_content(
        self, strategy_id: str, artifact_fingerprint: str
    ) -> StrategyGenerationProvenance | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(StrategyGenerationProvenanceRow)
                .join(
                    GeneratedStrategyArtifactRow,
                    GeneratedStrategyArtifactRow.id == StrategyGenerationProvenanceRow.artifact_id,
                )
                .where(
                    StrategyGenerationProvenanceRow.strategy_id == strategy_id,
                    GeneratedStrategyArtifactRow.content_fingerprint == artifact_fingerprint,
                )
            )
        if row is None:
            return None
        return StrategyGenerationProvenance(
            row.id,
            row.request_id,
            row.source_snapshot_id,
            row.draft_id,
            row.artifact_id,
            row.validation_report_id,
            row.strategy_id,
            row.strategy_version,
            row.model_provider,
            row.model_id,
            row.model_version,
            row.prompt_template_version,
            row.generated_at,
            row.confirmed_at,
            row.confirmed_by,
            row.activation_policy_version,
        )

    async def purge_expired_raw_sources(self, now: datetime, *, batch_size: int) -> int:
        async with self._sessions() as session, session.begin():
            identities = (
                await session.scalars(
                    select(StrategySourceSnapshotRow.id)
                    .where(
                        StrategySourceSnapshotRow.encrypted_content.is_not(None),
                        StrategySourceSnapshotRow.raw_content_expires_at <= now,
                    )
                    .order_by(StrategySourceSnapshotRow.raw_content_expires_at)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()
            if identities:
                await session.execute(
                    update(StrategySourceSnapshotRow)
                    .where(StrategySourceSnapshotRow.id.in_(identities))
                    .values(
                        encrypted_content=None,
                        encryption_key_id=None,
                        raw_content_purged_at=now,
                    )
                )
            request_ids = (
                await session.scalars(
                    select(StrategyGenerationRequestRow.id)
                    .where(
                        StrategyGenerationRequestRow.protected_submitted_value.is_not(None),
                        StrategyGenerationRequestRow.submitted_value_expires_at <= now,
                    )
                    .order_by(StrategyGenerationRequestRow.submitted_value_expires_at)
                    .limit(max(0, batch_size - len(identities)))
                    .with_for_update(skip_locked=True)
                )
            ).all()
            if request_ids:
                await session.execute(
                    update(StrategyGenerationRequestRow)
                    .where(StrategyGenerationRequestRow.id.in_(request_ids))
                    .values(
                        protected_submitted_value=None,
                        submitted_value_key_id=None,
                        submitted_value_purged_at=now,
                    )
                )
            return len(identities) + len(request_ids)


def _source_values(value: StrategySourceSnapshot) -> dict[str, object]:
    return {
        name: getattr(value, name)
        for name in (
            "id",
            "submitted_url",
            "canonical_url",
            "title",
            "attribution",
            "retrieved_at",
            "content_fingerprint",
            "encrypted_content",
            "encryption_key_id",
            "media_type",
            "size",
            "access_policy_version",
            "raw_content_expires_at",
            "raw_content_purged_at",
        )
    } | {"source_type": value.source_type.value, "retention_class": value.retention_class.value}


def _draft_values(value: GeneratedStrategyDraft) -> dict[str, object]:
    definitions = [
        {
            "name": item.name,
            "description": item.description,
            "valueType": item.value_type.value,
            "default": None if item.default_value is None else str(item.default_value),
            "minimum": None if item.minimum is None else str(item.minimum),
            "maximum": None if item.maximum is None else str(item.maximum),
        }
        for item in value.parameter_schema.definitions
    ]
    return {
        "id": value.id,
        "generation_request_id": value.generation_request_id,
        "source_snapshot_id": value.source_snapshot_id,
        "candidate_index": value.candidate_index,
        "normalized_name": value.normalized_name,
        "display_name": value.display_name,
        "description": value.description,
        "structured_rules": dict(value.structured_rules),
        "parameter_schema": {
            "definitions": definitions,
            "relationships": [
                [r.left, r.operator, r.right] for r in value.parameter_schema.relationship_rules
            ],
        },
        "assumptions": list(value.assumptions),
        "evidence": [
            {
                "ruleId": i.rule_id,
                "excerpt": i.source_excerpt,
                "location": i.source_location,
                "inferred": i.inferred,
            }
            for i in value.evidence
        ],
        "status": value.status.value,
        "draft_fingerprint": value.draft_fingerprint,
        "generated_artifact_id": value.generated_artifact_id,
        "validation_report_id": value.validation_report_id,
        "failure_issues": [
            {"field": item.field, "code": item.code, "message": item.message}
            for item in value.failure_issues
        ],
    }


def _to_draft(row: GeneratedStrategyDraftRow) -> GeneratedStrategyDraft:
    definition_values = cast(list[dict[str, object]], row.parameter_schema["definitions"])
    relationship_values = cast(list[list[str]], row.parameter_schema["relationships"])
    definitions = tuple(
        ParameterDefinition(
            str(item["name"]),
            str(item["description"]),
            ParameterValueType(str(item["valueType"])),
            _stored_scalar(item.get("default"), str(item["valueType"])),
            _stored_scalar(item.get("minimum"), str(item["valueType"])),
            _stored_scalar(item.get("maximum"), str(item["valueType"])),
        )
        for item in definition_values
    )
    relationships = tuple(RelationshipRule(*item) for item in relationship_values)
    evidence = tuple(
        RuleEvidence(
            str(i["ruleId"]),
            str(i["excerpt"]),
            None if i.get("location") is None else str(i["location"]),
            bool(i["inferred"]),
        )
        for i in row.evidence
    )
    return GeneratedStrategyDraft(
        row.id,
        row.generation_request_id,
        row.source_snapshot_id,
        row.candidate_index,
        row.normalized_name,
        row.display_name,
        row.description,
        row.structured_rules,
        ParameterSchema(definitions, relationships),
        tuple(row.assumptions),
        evidence,
        DraftStatus(row.status),
        row.generated_artifact_id,
        row.validation_report_id,
        tuple(
            ErrorIssue(
                None if item.get("field") is None else str(item["field"]),
                str(item["code"]),
                str(item["message"]),
            )
            for item in row.failure_issues
        ),
    )


def _stored_scalar(value: object, value_type: str) -> int | Decimal | None:
    if value is None:
        return None
    return (
        int(str(value)) if value_type == ParameterValueType.INTEGER.value else Decimal(str(value))
    )
