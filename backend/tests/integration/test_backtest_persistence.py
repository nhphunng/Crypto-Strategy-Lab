from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from crypto_lab.domain.backtest.configuration import BacktestRun, RunStatus
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.backtest_models import (
    BacktestEquityPointRow,
    BacktestResultRow,
    BacktestSignalSnapshotRow,
    BacktestTradeRow,
)
from tests.fixtures.backtest_evaluation.persistence import BacktestPersistenceContext
from tests.integration.test_migrations import TEST_DATABASE_URL, run_alembic, table_names

pytestmark = pytest.mark.integration


async def test_result_and_children_persist_atomically_and_resolve_idempotently(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    context = persisted_backtest
    resolved = await context.repository.save_result(context.result)
    assert resolved.id == context.result.id
    async with context.database.sessions() as session:
        counts = []
        for model in (
            BacktestResultRow,
            BacktestSignalSnapshotRow,
            BacktestTradeRow,
            BacktestEquityPointRow,
        ):
            counts.append(await session.scalar(select(func.count()).select_from(model)))

    assert tuple(counts) == (
        1,
        len(context.result.signals),
        len(context.result.trades),
        len(context.result.equity_curve.points),
    )


async def test_duplicate_job_id_with_different_inputs_fails_closed(
    backtest_context: BacktestPersistenceContext,
) -> None:
    context = backtest_context
    conflicting = replace(
        context.result.configuration, initial_capital=Decimal("2000")
    )
    with pytest.raises(BacktestError) as caught:
        await context.repository.create_or_resolve_run(
            BacktestRun(conflicting, RunStatus.REQUESTED, context.run.requested_at)
        )

    assert caught.value.code is BacktestErrorCode.JOB_CONFLICT
    stored = await context.repository.get_run(context.run.configuration.run_id)
    assert stored is not None
    assert stored.configuration.initial_capital == Decimal("1000")


async def test_completed_run_is_terminal(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    context = persisted_backtest
    stored = await context.repository.get_run(context.run.configuration.run_id)
    assert stored is not None and stored.status is RunStatus.COMPLETED

    with pytest.raises(BacktestError) as caught:
        await context.repository.update_run(stored)

    assert caught.value.code is BacktestErrorCode.JOB_CONFLICT


async def test_feature004_migration_upgrades_and_downgrades_as_one_unit() -> None:
    database = Database.create(TEST_DATABASE_URL)
    if not await database.ping():
        await database.dispose()
        pytest.skip("PostgreSQL integration database is unavailable")
    await database.dispose()

    run_alembic("downgrade", "20260813_003_strategy")
    assert "backtest_results" not in await table_names()
    run_alembic("upgrade", "20260813_004_backtest")
    assert {
        "backtest_runs",
        "backtest_results",
        "backtest_trades",
        "backtest_equity_points",
        "evaluation_results",
    } <= await table_names()
    run_alembic("downgrade", "20260813_003_strategy")
    assert "backtest_results" not in await table_names()
    run_alembic("upgrade", "head")
