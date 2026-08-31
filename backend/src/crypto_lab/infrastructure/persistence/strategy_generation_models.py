from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class StrategyGenerationRequestRow(Base):
    __tablename__ = "strategy_generation_requests"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    protected_submitted_value: Mapped[bytes | None] = mapped_column(LargeBinary)
    submitted_value_key_id: Mapped[str | None] = mapped_column(String(255))
    submitted_value_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    submitted_value_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("strategy_source_snapshots.id")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failure_category: Mapped[str | None] = mapped_column(String(64))
    failure_message: Mapped[str | None] = mapped_column(Text)


class StrategySourceSnapshotRow(Base):
    __tablename__ = "strategy_source_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "content_fingerprint", "canonical_url", name="uq_strategy_source_identity"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_url: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_content: Mapped[bytes | None] = mapped_column(LargeBinary)
    encryption_key_id: Mapped[str | None] = mapped_column(String(255))
    media_type: Mapped[str | None] = mapped_column(String(128))
    size: Mapped[int | None] = mapped_column(Integer)
    access_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    retention_class: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_content_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_content_purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GeneratedStrategyDraftRow(Base):
    __tablename__ = "generated_strategy_drafts"
    __table_args__ = (
        UniqueConstraint(
            "generation_request_id", "candidate_index", name="uq_generated_draft_candidate"
        ),
        UniqueConstraint(
            "generation_request_id", "draft_fingerprint", name="uq_generated_draft_fingerprint"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    generation_request_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_generation_requests.id"), nullable=False
    )
    source_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_source_snapshots.id"), nullable=False
    )
    candidate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    structured_rules: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    parameter_schema: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    draft_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_artifact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generated_strategy_artifacts.id")
    )
    validation_report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("strategy_validation_reports.id")
    )
    failure_issues: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False, default=list
    )


class GeneratedStrategyArtifactRow(Base):
    __tablename__ = "generated_strategy_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "content_fingerprint", "contract_version", name="uq_generated_artifact_content"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    draft_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_strategy_drafts.id"), nullable=False
    )
    content_reference: Mapped[str] = mapped_column(Text, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    declared_imports: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    capabilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    language_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StrategyValidationReportRow(Base):
    __tablename__ = "strategy_validation_reports"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("generated_strategy_artifacts.id"), nullable=False
    )
    artifact_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    checks: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    findings: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    environment_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class StrategyGenerationProvenanceRow(Base):
    __tablename__ = "strategy_generation_provenance"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("strategy_generation_requests.id"))
    source_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_source_snapshots.id")
    )
    draft_id: Mapped[UUID] = mapped_column(ForeignKey("generated_strategy_drafts.id"))
    artifact_id: Mapped[UUID] = mapped_column(ForeignKey("generated_strategy_artifacts.id"))
    validation_report_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_validation_reports.id")
    )
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    activation_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
