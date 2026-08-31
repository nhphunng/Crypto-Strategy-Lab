"""Create durable generated-strategy provenance and activation storage.

Revision ID: 20260823_006_generation
Revises: 20260813_005_leaderboard
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260823_006_generation"
down_revision: str | None = "20260813_005_leaderboard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_generation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("protected_submitted_value", sa.LargeBinary(), nullable=True),
        sa.Column("submitted_value_key_id", sa.String(255), nullable=True),
        sa.Column("submitted_value_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_value_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('RECEIVED','SOURCE_PREPARING','GENERATING','COMPLETED','FAILED')",
            name="ck_strategy_generation_requests_status",
        ),
    )
    op.create_table(
        "strategy_source_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("submitted_url", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("encrypted_content", sa.LargeBinary(), nullable=True),
        sa.Column("encryption_key_id", sa.String(255), nullable=True),
        sa.Column("media_type", sa.String(128), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("access_policy_version", sa.String(64), nullable=False),
        sa.Column("retention_class", sa.String(32), nullable=False),
        sa.Column("raw_content_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_content_purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "content_fingerprint", "canonical_url", name="uq_strategy_source_identity"
        ),
    )
    op.create_table(
        "generated_strategy_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "generation_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_generation_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "source_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_source_snapshots.id"),
            nullable=False,
        ),
        sa.Column("candidate_index", sa.Integer(), nullable=False),
        sa.Column("normalized_name", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("structured_rules", postgresql.JSONB(), nullable=False),
        sa.Column("parameter_schema", postgresql.JSONB(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("draft_fingerprint", sa.String(64), nullable=False),
        sa.Column("generated_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("validation_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "failure_issues",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.UniqueConstraint(
            "generation_request_id", "candidate_index", name="uq_generated_draft_candidate"
        ),
        sa.UniqueConstraint(
            "generation_request_id", "draft_fingerprint", name="uq_generated_draft_fingerprint"
        ),
    )
    op.create_table(
        "generated_strategy_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generated_strategy_drafts.id"),
            nullable=False,
        ),
        sa.Column("content_reference", sa.Text(), nullable=False),
        sa.Column("content_fingerprint", sa.String(64), nullable=False),
        sa.Column("contract_version", sa.String(32), nullable=False),
        sa.Column("declared_imports", postgresql.JSONB(), nullable=False),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False),
        sa.Column("language", sa.String(32), nullable=False),
        sa.Column("language_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "content_fingerprint", "contract_version", name="uq_generated_artifact_content"
        ),
    )
    op.create_table(
        "strategy_validation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("generated_strategy_artifacts.id"),
            nullable=False,
        ),
        sa.Column("artifact_fingerprint", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("checks", postgresql.JSONB(), nullable=False),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("environment_fingerprint", sa.String(64), nullable=False),
    )
    op.create_table(
        "strategy_generation_provenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(64), nullable=False),
        sa.Column("strategy_version", sa.String(32), nullable=False),
        sa.Column("model_provider", sa.String(128), nullable=False),
        sa.Column("model_id", sa.String(128), nullable=False),
        sa.Column("model_version", sa.String(128), nullable=False),
        sa.Column("prompt_template_version", sa.String(64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", sa.String(255), nullable=False),
        sa.Column("activation_policy_version", sa.String(64), nullable=False),
    )
    op.add_column(
        "strategy_definitions",
        sa.Column("origin", sa.String(32), server_default="BUILT_IN", nullable=False),
    )
    op.add_column(
        "strategy_definitions",
        sa.Column("generated_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "strategy_definitions",
        sa.Column("generation_provenance_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_strategy_definitions_generated_references",
        "strategy_definitions",
        "(origin = 'BUILT_IN' AND generated_artifact_id IS NULL AND generation_provenance_id IS NULL) OR "
        "(origin = 'LLM_GENERATED' AND generated_artifact_id IS NOT NULL AND generation_provenance_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_strategy_definitions_generated_references", "strategy_definitions", type_="check"
    )
    op.drop_column("strategy_definitions", "generation_provenance_id")
    op.drop_column("strategy_definitions", "generated_artifact_id")
    op.drop_column("strategy_definitions", "origin")
    op.drop_table("strategy_generation_provenance")
    op.drop_table("strategy_validation_reports")
    op.drop_table("generated_strategy_artifacts")
    op.drop_table("generated_strategy_drafts")
    op.drop_table("strategy_source_snapshots")
    op.drop_table("strategy_generation_requests")
