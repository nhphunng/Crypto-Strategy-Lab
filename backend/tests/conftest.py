from __future__ import annotations

import os
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from crypto_lab.api.dependencies import build_container
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from crypto_lab.infrastructure.persistence.repositories.news_repository import (
    SqlAlchemyNewsRepository,
)
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app
from tests.fixtures.backtest_evaluation.persistence import (
    BacktestPersistenceContext,
    persist_backtest,
    prepare_backtest_context,
)
from tests.fixtures.leaderboard import (
    LeaderboardFixture,
    reset_leaderboard_fixture,
    seed_leaderboard_fixture,
)
from tests.support.lifespan import LifespanManager

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


@pytest.fixture
async def leaderboard_database() -> AsyncIterator[Database]:
    """A clean PostgreSQL database for leaderboard projection tests."""

    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    async with database.sessions() as session, session.begin():
        await reset_leaderboard_fixture(session)
    yield database
    async with database.sessions() as session, session.begin():
        await reset_leaderboard_fixture(session)
    await database.dispose()


@pytest.fixture
async def seeded_leaderboard(leaderboard_database: Database) -> LeaderboardFixture:
    async with leaderboard_database.sessions() as session, session.begin():
        return await seed_leaderboard_fixture(session)


@pytest.fixture
async def leaderboard_app(leaderboard_database: Database) -> AsyncIterator[FastAPI]:
    container = build_container(Settings(database_url=TEST_DATABASE_URL))
    app = create_app(container)
    async with LifespanManager(app):
        yield app


@pytest.fixture
async def leaderboard_client(leaderboard_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=leaderboard_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def news_repository() -> AsyncIterator[SqlAlchemyNewsRepository]:
    """A clean PostgreSQL news_items table backed by the idempotent repository."""

    from crypto_lab.infrastructure.persistence.repositories.news_repository import (
        SqlAlchemyNewsRepository,
    )

    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    async with database.engine.begin() as connection:
        await connection.execute(text("TRUNCATE news_items"))
    yield SqlAlchemyNewsRepository(database.sessions)
    async with database.engine.begin() as connection:
        await connection.execute(text("TRUNCATE news_items"))
    await database.dispose()


@pytest.fixture
async def backtest_database() -> AsyncIterator[Database]:
    """A clean PostgreSQL database for Feature 004 persistence tests."""

    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    async with database.sessions() as session, session.begin():
        await reset_leaderboard_fixture(session)
    yield database
    async with database.sessions() as session, session.begin():
        await reset_leaderboard_fixture(session)
    await database.dispose()


@pytest.fixture
async def backtest_context(backtest_database: Database) -> BacktestPersistenceContext:
    return await prepare_backtest_context(backtest_database)


@pytest.fixture
async def persisted_backtest(
    backtest_context: BacktestPersistenceContext,
) -> BacktestPersistenceContext:
    await persist_backtest(backtest_context)
    return backtest_context
