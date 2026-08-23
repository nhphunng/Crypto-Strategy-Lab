from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import text

from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.implementations.moving_average import MovingAverageStrategy
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.repositories.strategy_definition_repository import (
    SqlAlchemyStrategyDefinitionRepository,
)
from tests.conftest import TEST_DATABASE_URL


@pytest.mark.integration
async def test_real_postgres_definition_create_is_idempotent_and_exact() -> None:
    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    async with database.sessions() as session:
        exists = await session.scalar(text("SELECT to_regclass('public.strategy_definitions')"))
    if exists is None:
        await database.dispose()
        pytest.skip("strategy migrations are not applied")
    strategy = MovingAverageStrategy()
    definition = StrategyDefinition(
        UUID(int=9101),
        strategy.metadata.strategy_id,
        strategy.metadata.strategy_type,
        strategy.metadata.strategy_version,
        strategy.metadata.contract_version,
        strategy.validate_parameters({"period": 20}),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    repository = SqlAlchemyStrategyDefinitionRepository(database.sessions)
    first = await repository.create_or_resolve(definition)
    second = await repository.create_or_resolve(definition)
    assert first.id == second.id
    assert (await repository.get(first.id)) == first
    await database.dispose()
