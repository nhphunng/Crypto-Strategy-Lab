from pathlib import Path

from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow


def test_strategy_definition_mapping_and_migration_have_immutable_constraints() -> None:
    constraints = {item.name for item in StrategyDefinitionRow.__table__.constraints}
    indexes = {item.name for item in StrategyDefinitionRow.__table__.indexes}
    assert "uq_strategy_definitions_content_fingerprint" in constraints
    assert "ix_strategy_definitions_strategy_version" in indexes
    migration = (
        Path(__file__).parents[2]
        / "migrations/versions/20260813_003_create_strategy_definitions.py"
    ).read_text()
    assert "def upgrade()" in migration and "def downgrade()" in migration
    assert 'op.drop_table("strategy_definitions")' in migration
