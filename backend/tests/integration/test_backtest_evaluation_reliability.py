from __future__ import annotations

import asyncio
from dataclasses import replace
from uuid import UUID

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from crypto_lab.application.backtests.execute_run import ExecuteBacktestRun
from crypto_lab.domain.backtest.configuration import RunStatus
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode
from crypto_lab.infrastructure.persistence.backtest_models import (
    BacktestResultRow,
    BacktestSignalSnapshotRow,
    BacktestTradeRow,
)
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.persistence import BacktestPersistenceContext

pytestmark = pytest.mark.integration


class _Clock:
    def now(self):
        return NOW


class _MissingDataset:
    async def get_complete(self, _dataset_id):
        return None


class _UnusedStrategy:
    async def analyze(self, *_args):
        raise AssertionError("strategy must not run without a complete dataset")


async def test_child_insert_failure_rolls_back_the_entire_result(
    backtest_context: BacktestPersistenceContext,
) -> None:
    context = backtest_context
    broken_trade = replace(
        context.result.trades[0], exit_signal_snapshot_id=UUID(int=999_999)
    )
    broken = replace(
        context.result, trades=(broken_trade, *context.result.trades[1:])
    )

    with pytest.raises(IntegrityError):
        await context.repository.save_result(broken)

    async with context.database.sessions() as session:
        counts = []
        for model in (BacktestResultRow, BacktestSignalSnapshotRow, BacktestTradeRow):
            counts.append(await session.scalar(select(func.count()).select_from(model)))
    assert counts == [0, 0, 0]


async def test_concurrent_duplicate_submission_creates_one_complete_result(
    backtest_context: BacktestPersistenceContext,
) -> None:
    context = backtest_context
    first, second = await asyncio.gather(
        context.repository.save_result(context.result),
        context.repository.save_result(context.result),
    )
    assert first.id == second.id == context.result.id
    async with context.database.sessions() as session:
        result_count = await session.scalar(
            select(func.count()).select_from(BacktestResultRow)
        )
        signal_count = await session.scalar(
            select(func.count()).select_from(BacktestSignalSnapshotRow)
        )
        trade_count = await session.scalar(
            select(func.count()).select_from(BacktestTradeRow)
        )
    assert (result_count, signal_count, trade_count) == (
        1,
        len(context.result.signals),
        len(context.result.trades),
    )


async def test_checksum_corruption_is_detected_on_idempotent_replay(
    persisted_backtest: BacktestPersistenceContext,
) -> None:
    context = persisted_backtest
    async with context.database.sessions() as session, session.begin():
        await session.execute(
            update(BacktestResultRow)
            .where(BacktestResultRow.id == context.result.id)
            .values(result_checksum="f" * 64)
        )

    with pytest.raises(BacktestError) as caught:
        await context.repository.save_result(context.result)
    assert caught.value.code is BacktestErrorCode.JOB_CONFLICT


async def test_dependency_failure_is_terminal_safe_and_has_no_partial_result(
    backtest_context: BacktestPersistenceContext,
) -> None:
    context = backtest_context
    execute = ExecuteBacktestRun(
        context.repository,
        _MissingDataset(),
        _UnusedStrategy(),
        context.repository,
        _Clock(),
    )

    with pytest.raises(BacktestError) as caught:
        await execute.execute(context.run.configuration.run_id, "request-safe-failure")

    assert caught.value.code is BacktestErrorCode.DATASET_INELIGIBLE
    assert "secret" not in caught.value.message.lower()
    stored = await context.repository.get_run(context.run.configuration.run_id)
    assert stored is not None
    assert stored.status is RunStatus.FAILED
    assert stored.failure_code == "BACKTEST_DATASET_INELIGIBLE"
    assert await context.repository.get_result_for_run(context.run.configuration.run_id) is None
