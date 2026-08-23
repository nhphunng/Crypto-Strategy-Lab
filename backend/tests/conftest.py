from __future__ import annotations

import os
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from sqlalchemy import text

from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)


@pytest.fixture
def decimal_value():
    """Construct exact fixture values; strategy tests must never use binary floats."""

    def build(value: str | int) -> Decimal:
        return Decimal(value)

    return build


@pytest.fixture
async def postgres_repository() -> AsyncIterator[SqlAlchemyMarketDataRepository]:
    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    async with database.engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE candle_dataset_members, candle_datasets, candles CASCADE")
        )
    yield SqlAlchemyMarketDataRepository(database.sessions)
    async with database.engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE candle_dataset_members, candle_datasets, candles CASCADE")
        )
    await database.dispose()
