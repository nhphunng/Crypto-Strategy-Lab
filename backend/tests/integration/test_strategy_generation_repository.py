from pathlib import Path

from crypto_lab.infrastructure.persistence.strategy_generation_models import (
    GeneratedStrategyArtifactRow,
    GeneratedStrategyDraftRow,
    StrategyGenerationProvenanceRow,
    StrategyGenerationRequestRow,
    StrategySourceSnapshotRow,
    StrategyValidationReportRow,
)


def test_generation_migration_covers_all_durable_activation_aggregates() -> None:
    assert {
        StrategyGenerationRequestRow.__tablename__,
        StrategySourceSnapshotRow.__tablename__,
        GeneratedStrategyDraftRow.__tablename__,
        GeneratedStrategyArtifactRow.__tablename__,
        StrategyValidationReportRow.__tablename__,
        StrategyGenerationProvenanceRow.__tablename__,
    } == {
        "strategy_generation_requests",
        "strategy_source_snapshots",
        "generated_strategy_drafts",
        "generated_strategy_artifacts",
        "strategy_validation_reports",
        "strategy_generation_provenance",
    }
    migration = (
        Path(__file__).parents[2] / "migrations/versions/20260823_006_strategy_generation.py"
    ).read_text()
    assert "ck_strategy_definitions_generated_references" in migration
    assert "def downgrade()" in migration
