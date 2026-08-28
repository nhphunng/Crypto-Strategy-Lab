from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.domain.backtest.configuration import BacktestRun, RunStatus
from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.strategy.signal import SignalAction
from crypto_lab.infrastructure.database import Database
from crypto_lab.infrastructure.persistence.models import CandleDatasetRow
from crypto_lab.infrastructure.persistence.repositories.backtest_repository import (
    SqlAlchemyBacktestRepository,
)
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow
from tests.fixtures.backtest_evaluation.cross_feature import NOW, deterministic_inputs


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def two_trade_result() -> BacktestResult:
    configuration, candles, analysis, policy = deterministic_inputs(
        (
            SignalAction.BUY,
            SignalAction.SELL,
            SignalAction.BUY,
            SignalAction.SELL,
            SignalAction.HOLD,
        ),
        ("100", "100", "120", "100", "130"),
    )
    return execute_backtest(configuration, candles, analysis, policy, created_at=NOW)


@dataclass(frozen=True, slots=True)
class BacktestPersistenceContext:
    database: Database
    repository: SqlAlchemyBacktestRepository
    run: BacktestRun
    result: BacktestResult


async def prepare_backtest_context(database: Database) -> BacktestPersistenceContext:
    result = two_trade_result()
    configuration = result.configuration
    async with database.sessions() as session, session.begin():
        await _seed_dataset_and_strategy(session, result)

    repository = SqlAlchemyBacktestRepository(database.sessions)
    _, _, _, policy = deterministic_inputs(
        (SignalAction.HOLD, SignalAction.HOLD), ("100", "100")
    )
    await repository.ensure_policy(policy, NOW)
    run = await repository.create_or_resolve_run(
        BacktestRun(configuration, RunStatus.REQUESTED, NOW)
    )
    return BacktestPersistenceContext(database, repository, run, result)


async def persist_backtest(context: BacktestPersistenceContext) -> BacktestResult:
    running = context.run.running(NOW + timedelta(seconds=1))
    await context.repository.update_run(running)
    result = await context.repository.save_result(context.result)
    await context.repository.update_run(running.completed(NOW + timedelta(seconds=2)))
    return result


async def _seed_dataset_and_strategy(
    session: AsyncSession, result: BacktestResult
) -> None:
    configuration = result.configuration
    session.add(
        CandleDatasetRow(
            id=configuration.dataset_id,
            request_key=_hash("feature004-persistence-dataset"),
            schema_version=configuration.dataset_schema_version,
            provider=configuration.provider,
            pair=configuration.pair,
            timeframe=configuration.timeframe.value,
            start_time=configuration.start_time,
            end_time=configuration.end_time,
            status="COMPLETE",
            candle_count=len(result.equity_curve.points),
            checksum=configuration.dataset_checksum,
            build_token=None,
            lease_expires_at=None,
            failure_code=None,
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )
    )
    session.add(
        StrategyDefinitionRow(
            id=configuration.strategy_definition_id,
            strategy_id=configuration.strategy_id,
            strategy_type="MA",
            strategy_version=configuration.strategy_version,
            contract_version=configuration.contract_version,
            parameters={"period": 2},
            parameter_schema_fingerprint=_hash("feature004-parameter-schema"),
            content_fingerprint=_hash("feature004-strategy-definition"),
            created_at=NOW,
        )
    )
    await session.flush()
