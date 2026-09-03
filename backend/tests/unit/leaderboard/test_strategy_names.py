"""Names come from versioned metadata, while immutable strategy IDs stay intact."""

from unittest.mock import AsyncMock
from uuid import uuid4

from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.strategy.registry import RegistryStatus
from crypto_lab.infrastructure.persistence.evaluation_models import EvaluationResultRow
from crypto_lab.infrastructure.persistence.repositories.leaderboard_repository import (
    _strategy_names,
    _strategy_summary,
)
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow


async def test_catalog_name_replaces_internal_id_without_changing_identity() -> None:
    registry = build_strategy_registry()
    entry = next(item for item in registry.discover() if item.strategy_id == "bollinger")
    definition = StrategyDefinitionRow(
        id=uuid4(),
        strategy_id=entry.strategy_id,
        strategy_version=str(entry.strategy_version),
        strategy_type="INDICATOR",
        parameters={},
    )
    evaluation = EvaluationResultRow(
        strategy_id=definition.strategy_id,
        strategy_version=definition.strategy_version,
    )
    session = AsyncMock()

    names = await _strategy_names(session, [definition], registry)
    summary = _strategy_summary(evaluation, definition, names[definition.id])

    assert summary.display_name == "Bollinger Bands Mean Reversion"
    assert summary.strategy_id == "bollinger"
    assert summary.strategy_version == str(entry.strategy_version)
    session.execute.assert_not_called()


async def test_explicit_names_and_unknown_versions_keep_their_existing_fallbacks() -> None:
    explicit = StrategyDefinitionRow(
        id=uuid4(),
        strategy_id="bollinger",
        strategy_version="1.0.0",
        strategy_type="INDICATOR",
        parameters={"displayName": "Recorded custom name"},
    )
    unknown_version = StrategyDefinitionRow(
        id=uuid4(),
        strategy_id="bollinger",
        strategy_version="99.0.0",
        strategy_type="INDICATOR",
        parameters={},
    )
    evaluation = EvaluationResultRow(strategy_id="bollinger", strategy_version="99.0.0")
    session = AsyncMock()

    names = await _strategy_names(
        session, [explicit, unknown_version, None], build_strategy_registry()
    )

    assert names == {explicit.id: "Recorded custom name"}
    assert _strategy_summary(evaluation, unknown_version).display_name == "bollinger"
    assert _strategy_summary(evaluation, None).display_name == "bollinger"
    session.execute.assert_not_called()


async def test_registry_entries_added_after_startup_and_unavailable_entries_have_names() -> None:
    from crypto_lab.domain.strategy.registry import StrategyRegistry
    from crypto_lab.domain.strategy.version import ContractVersionRange

    registry = StrategyRegistry(ContractVersionRange(1, 0, 0))
    entry = build_strategy_registry().discover()[0]
    definition = StrategyDefinitionRow(
        id=uuid4(),
        strategy_id=entry.strategy_id,
        strategy_version=str(entry.strategy_version),
        strategy_type="INDICATOR",
        parameters={},
    )
    session = AsyncMock()
    assert await _strategy_names(session, [definition], registry) == {}

    registry.register(entry.strategy, status=RegistryStatus.UNAVAILABLE)

    assert await _strategy_names(session, [definition], registry) == {
        definition.id: entry.metadata.display_name,
    }
