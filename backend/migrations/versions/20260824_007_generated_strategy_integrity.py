"""Repair and enforce generated-strategy reference integrity.

Revision ID: 20260824_007_integrity
Revises: 20260823_006_generation
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260824_007_integrity"
down_revision: str | None = "20260823_006_generation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Early Feature 003 deployments did not constrain provenance references. Repair any
    # dangling activation references from the activated draft before enforcing integrity.
    op.execute(
        """
        UPDATE strategy_generation_provenance AS provenance
        SET artifact_id = draft.generated_artifact_id,
            validation_report_id = draft.validation_report_id
        FROM generated_strategy_drafts AS draft
        WHERE provenance.draft_id = draft.id
          AND draft.generated_artifact_id IS NOT NULL
          AND draft.validation_report_id IS NOT NULL
          AND (
            NOT EXISTS (
              SELECT 1 FROM generated_strategy_artifacts AS artifact
              WHERE artifact.id = provenance.artifact_id
            )
            OR NOT EXISTS (
              SELECT 1 FROM strategy_validation_reports AS report
              WHERE report.id = provenance.validation_report_id
            )
          )
        """
    )
    op.execute(
        """
        UPDATE strategy_definitions AS definition
        SET generated_artifact_id = provenance.artifact_id
        FROM strategy_generation_provenance AS provenance
        WHERE definition.generation_provenance_id = provenance.id
          AND definition.origin = 'LLM_GENERATED'
          AND definition.generated_artifact_id IS DISTINCT FROM provenance.artifact_id
        """
    )

    _foreign_key(
        "fk_generation_requests_source_snapshot",
        "strategy_generation_requests",
        "strategy_source_snapshots",
        ["source_snapshot_id"],
        ["id"],
    )
    _foreign_key(
        "fk_generated_drafts_artifact",
        "generated_strategy_drafts",
        "generated_strategy_artifacts",
        ["generated_artifact_id"],
        ["id"],
    )
    _foreign_key(
        "fk_generated_drafts_validation_report",
        "generated_strategy_drafts",
        "strategy_validation_reports",
        ["validation_report_id"],
        ["id"],
    )
    for name, column, target in (
        ("fk_generation_provenance_request", "request_id", "strategy_generation_requests"),
        ("fk_generation_provenance_source", "source_snapshot_id", "strategy_source_snapshots"),
        ("fk_generation_provenance_draft", "draft_id", "generated_strategy_drafts"),
        ("fk_generation_provenance_artifact", "artifact_id", "generated_strategy_artifacts"),
        (
            "fk_generation_provenance_validation_report",
            "validation_report_id",
            "strategy_validation_reports",
        ),
    ):
        _foreign_key(name, "strategy_generation_provenance", target, [column], ["id"])
    _foreign_key(
        "fk_strategy_definitions_generated_artifact",
        "strategy_definitions",
        "generated_strategy_artifacts",
        ["generated_artifact_id"],
        ["id"],
    )
    _foreign_key(
        "fk_strategy_definitions_generation_provenance",
        "strategy_definitions",
        "strategy_generation_provenance",
        ["generation_provenance_id"],
        ["id"],
    )


def downgrade() -> None:
    for table, name in (
        ("strategy_definitions", "fk_strategy_definitions_generation_provenance"),
        ("strategy_definitions", "fk_strategy_definitions_generated_artifact"),
        (
            "strategy_generation_provenance",
            "fk_generation_provenance_validation_report",
        ),
        ("strategy_generation_provenance", "fk_generation_provenance_artifact"),
        ("strategy_generation_provenance", "fk_generation_provenance_draft"),
        ("strategy_generation_provenance", "fk_generation_provenance_source"),
        ("strategy_generation_provenance", "fk_generation_provenance_request"),
        ("generated_strategy_drafts", "fk_generated_drafts_validation_report"),
        ("generated_strategy_drafts", "fk_generated_drafts_artifact"),
        ("strategy_generation_requests", "fk_generation_requests_source_snapshot"),
    ):
        op.drop_constraint(name, table, type_="foreignkey")


def _foreign_key(
    name: str,
    source: str,
    target: str,
    local_columns: list[str],
    remote_columns: list[str],
) -> None:
    op.create_foreign_key(name, source, target, local_columns, remote_columns)
