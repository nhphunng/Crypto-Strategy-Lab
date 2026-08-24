from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.domain.backtest.configuration import (
    BacktestConfiguration,
    BacktestRun,
    ExecutionPolicy,
    RunStatus,
)
from crypto_lab.domain.backtest.equity import EquityCurve, EquityPoint
from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode, NoOpCode
from crypto_lab.domain.backtest.result import (
    BacktestHistoryState,
    BacktestResult,
    SignalSnapshot,
    TradeState,
)
from crypto_lab.domain.backtest.trade import CloseReason, Trade, TradeSide
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.persistence.backtest_models import (
    BacktestEquityPointRow,
    BacktestResultRow,
    BacktestRunRow,
    BacktestSignalSnapshotRow,
    BacktestTradeRow,
    ExecutionPolicyRow,
)


class SqlAlchemyBacktestRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def ensure_policy(self, policy: ExecutionPolicy, created_at: object) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(ExecutionPolicyRow)
                .values(
                    id=policy.id,
                    policy_id=policy.policy_id,
                    version=policy.version,
                    fingerprint=policy.fingerprint,
                    rules=policy.rules,
                    created_at=created_at,
                )
                .on_conflict_do_nothing(index_elements=["policy_id", "version"])
            )
            row = await session.scalar(
                select(ExecutionPolicyRow).where(
                    ExecutionPolicyRow.policy_id == policy.policy_id,
                    ExecutionPolicyRow.version == policy.version,
                )
            )
            if row is None or row.fingerprint != policy.fingerprint:
                raise ValueError("execution policy identity conflicts with immutable rules")

    async def get(self, policy_id: UUID, version: str) -> ExecutionPolicy | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(ExecutionPolicyRow).where(
                    ExecutionPolicyRow.id == policy_id, ExecutionPolicyRow.version == version
                )
            )
        return None if row is None else ExecutionPolicy(row.id, row.policy_id, row.version)

    async def create_or_resolve_run(self, run: BacktestRun) -> BacktestRun:
        values = _run_values(run)
        async with self._sessions() as session, session.begin():
            await session.execute(
                insert(BacktestRunRow)
                .values(values)
                .on_conflict_do_nothing(index_elements=["job_id"])
            )
            row = await session.scalar(
                select(BacktestRunRow).where(BacktestRunRow.job_id == run.configuration.job_id)
            )
            if row is None:
                raise RuntimeError("backtest run could not be resolved")
            resolved = _run_domain(row)
            if resolved.configuration.input_fingerprint != run.configuration.input_fingerprint:
                raise BacktestError(
                    BacktestErrorCode.JOB_CONFLICT, "jobId already identifies different inputs"
                )
            return resolved

    async def get_run(self, run_id: UUID) -> BacktestRun | None:
        async with self._sessions() as session:
            row = await session.get(BacktestRunRow, run_id)
        return None if row is None else _run_domain(row)

    async def update_run(self, run: BacktestRun) -> None:
        async with self._sessions() as session, session.begin():
            row = await session.get(BacktestRunRow, run.configuration.run_id, with_for_update=True)
            if row is None:
                raise ValueError("backtest run is unavailable")
            current = RunStatus(row.status)
            allowed = (current is RunStatus.REQUESTED and run.status is RunStatus.RUNNING) or (
                current is RunStatus.RUNNING
                and run.status in (RunStatus.COMPLETED, RunStatus.FAILED)
            )
            if not allowed:
                raise BacktestError(BacktestErrorCode.JOB_CONFLICT, "invalid run state transition")
            row.status = run.status.value
            row.started_at = run.started_at
            row.completed_at = run.completed_at
            row.failure_code = run.failure_code

    async def save_result(self, result: BacktestResult) -> BacktestResult:
        async with self._sessions() as session, session.begin():
            inserted_id = await session.scalar(
                insert(BacktestResultRow)
                .values(_result_values(result))
                .on_conflict_do_nothing()
                .returning(BacktestResultRow.id)
            )
            if inserted_id is None:
                existing = await session.scalar(
                    select(BacktestResultRow).where(
                        (BacktestResultRow.job_id == result.configuration.job_id)
                        | (BacktestResultRow.input_fingerprint == result.input_fingerprint)
                        | (BacktestResultRow.result_checksum == result.result_checksum)
                    )
                )
                if existing is None:
                    raise RuntimeError("conflicting backtest result could not be resolved")
                if existing.result_checksum != result.result_checksum:
                    raise BacktestError(
                        BacktestErrorCode.JOB_CONFLICT, "job result content conflicts"
                    )
                return await _load_result(session, existing)
            config = result.configuration
            for snapshot in result.signals:
                await session.execute(
                    insert(BacktestSignalSnapshotRow).values(
                        _snapshot_values(result.id, snapshot, config)
                    )
                )
            for trade in result.trades:
                await session.execute(
                    insert(BacktestTradeRow).values(_trade_values(result.id, trade))
                )
            for point in result.equity_curve.points:
                await session.execute(
                    insert(BacktestEquityPointRow).values(_equity_values(result.id, point))
                )
            return result

    async def get_result(self, result_id: UUID) -> BacktestResult | None:
        async with self._sessions() as session:
            row = await session.get(BacktestResultRow, result_id)
            return None if row is None else await _load_result(session, row)

    async def get_result_for_run(self, run_id: UUID) -> BacktestResult | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(BacktestResultRow).where(BacktestResultRow.run_id == run_id)
            )
            if row is None:
                run_row = await session.get(BacktestRunRow, run_id)
                if run_row is not None:
                    fingerprint = _run_domain(run_row).configuration.input_fingerprint
                    row = await session.scalar(
                        select(BacktestResultRow).where(
                            BacktestResultRow.input_fingerprint == fingerprint
                        )
                    )
            return None if row is None else await _load_result(session, row)

    async def list_trades(
        self, result_id: UUID, cursor: str | None, limit: int
    ) -> tuple[tuple[Trade, ...], str | None]:
        offset = _cursor(cursor)
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(BacktestTradeRow)
                    .where(
                        BacktestTradeRow.backtest_result_id == result_id,
                        BacktestTradeRow.sequence >= offset,
                    )
                    .order_by(BacktestTradeRow.sequence)
                    .limit(limit + 1)
                )
            ).all()
        return tuple(_trade_domain(row) for row in rows[:limit]), str(rows[limit].sequence) if len(
            rows
        ) > limit else None

    async def result_counts(self, result_id: UUID) -> tuple[int, int] | None:
        async with self._sessions() as session:
            row = (
                await session.execute(
                    select(
                        BacktestResultRow.trade_count,
                        BacktestResultRow.equity_point_count,
                    ).where(BacktestResultRow.id == result_id)
                )
            ).one_or_none()
        return None if row is None else (row.trade_count, row.equity_point_count)

    async def list_equity(
        self, result_id: UUID, cursor: str | None, limit: int
    ) -> tuple[tuple[EquityPoint, ...], str | None]:
        offset = _cursor(cursor)
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(BacktestEquityPointRow)
                    .where(
                        BacktestEquityPointRow.backtest_result_id == result_id,
                        BacktestEquityPointRow.position >= offset,
                    )
                    .order_by(BacktestEquityPointRow.position)
                    .limit(limit + 1)
                )
            ).all()
        return tuple(_equity_domain(row) for row in rows[:limit]), str(rows[limit].position) if len(
            rows
        ) > limit else None


def _cursor(value: str | None) -> int:
    try:
        parsed = 0 if value is None else int(value)
    except ValueError as exc:
        raise ValueError("invalid cursor") from exc
    if parsed < 0:
        raise ValueError("invalid cursor")
    return parsed


def _run_values(run: BacktestRun) -> dict[str, object]:
    c = run.configuration
    return {
        "id": c.run_id,
        "job_id": c.job_id,
        "status": run.status.value,
        "dataset_id": c.dataset_id,
        "dataset_schema_version": c.dataset_schema_version,
        "dataset_checksum": c.dataset_checksum,
        "provider": c.provider,
        "pair": c.pair,
        "timeframe": c.timeframe.value,
        "start_time": c.start_time,
        "end_time": c.end_time,
        "strategy_definition_id": c.strategy_definition_id,
        "strategy_id": c.strategy_id,
        "strategy_version": c.strategy_version,
        "contract_version": c.contract_version,
        "parameter_fingerprint": c.parameter_fingerprint,
        "context_fingerprint": c.context_fingerprint,
        "execution_policy_id": c.execution_policy_id,
        "execution_policy_version": c.execution_policy_version,
        "initial_capital": c.initial_capital,
        "fee_rate": c.fee_rate,
        "slippage_rate": c.slippage_rate,
        "random_seed": c.random_seed,
        "requested_at": run.requested_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "failure_code": run.failure_code,
    }


def _run_domain(row: BacktestRunRow) -> BacktestRun:
    c = BacktestConfiguration(
        row.id,
        row.job_id,
        row.dataset_id,
        row.dataset_schema_version,
        row.dataset_checksum,
        row.provider,
        row.pair,
        Timeframe(row.timeframe),
        row.start_time,
        row.end_time,
        row.strategy_definition_id,
        row.strategy_id,
        row.strategy_version,
        row.contract_version,
        row.parameter_fingerprint,
        row.context_fingerprint,
        row.execution_policy_id,
        row.execution_policy_version,
        Decimal(row.initial_capital),
        Decimal(row.fee_rate),
        Decimal(row.slippage_rate),
        row.random_seed,
    )
    return BacktestRun(
        c,
        RunStatus(row.status),
        row.requested_at,
        row.started_at,
        row.completed_at,
        row.failure_code,
    )


def _result_values(result: BacktestResult) -> dict[str, object]:
    c = result.configuration
    return {
        "id": result.id,
        "run_id": c.run_id,
        "job_id": c.job_id,
        "input_fingerprint": c.input_fingerprint,
        "result_checksum": result.result_checksum,
        "history_state": result.history_state.value,
        "trade_state": result.trade_state.value,
        "initial_capital": c.initial_capital,
        "final_equity": result.final_equity,
        "signal_count": len(result.signals),
        "trade_count": len(result.trades),
        "equity_point_count": len(result.equity_curve.points),
        "execution_duration_ms": result.execution_duration_ms,
        "dataset_id": c.dataset_id,
        "dataset_checksum": c.dataset_checksum,
        "strategy_definition_id": c.strategy_definition_id,
        "execution_policy_id": c.execution_policy_id,
        "execution_policy_version": c.execution_policy_version,
        "execution_config_fingerprint": c.execution_config_fingerprint,
        "created_at": result.created_at,
    }


def _snapshot_values(
    result_id: UUID, s: SignalSnapshot, c: BacktestConfiguration
) -> dict[str, object]:
    reason = s.reason
    if s.no_op_code is not None:
        reason = f"NOOP:{s.no_op_code.value}" + (f"|{reason}" if reason else "")
    return {
        "id": s.id,
        "backtest_result_id": result_id,
        "source_signal_id": s.source_signal_id,
        "sequence": s.sequence,
        "timestamp": s.timestamp,
        "action": s.action,
        "phase": s.phase,
        "strength": s.strength,
        "reason": reason,
        "strategy_definition_id": c.strategy_definition_id,
        "strategy_id": c.strategy_id,
        "strategy_version": c.strategy_version,
        "contract_version": c.contract_version,
        "dataset_id": c.dataset_id,
        "dataset_schema_version": c.dataset_schema_version,
        "dataset_checksum": c.dataset_checksum,
        "analysis_result_fingerprint": c.context_fingerprint,
    }


def _trade_values(result_id: UUID, t: Trade) -> dict[str, object]:
    return {
        "id": t.id,
        "backtest_result_id": result_id,
        "sequence": t.sequence,
        "entry_signal_snapshot_id": t.entry_signal_snapshot_id,
        "exit_signal_snapshot_id": t.exit_signal_snapshot_id,
        "entry_time": t.entry_time,
        "exit_time": t.exit_time,
        "entry_reference_price": t.entry_reference_price,
        "exit_reference_price": t.exit_reference_price,
        "entry_price": t.entry_price,
        "exit_price": t.exit_price,
        "side": t.side.value,
        "quantity": t.quantity,
        "entry_fee": t.entry_fee,
        "exit_fee": t.exit_fee,
        "profit_loss": t.profit_loss,
        "return_percent": t.return_percent,
        "close_reason": t.close_reason.value,
    }


def _equity_values(result_id: UUID, p: EquityPoint) -> dict[str, object]:
    return {
        "id": p.id,
        "backtest_result_id": result_id,
        "position": p.position,
        "candle_open_time": p.candle_open_time,
        "valued_at": p.valued_at,
        "cash": p.cash,
        "quantity": p.quantity,
        "close_price": p.close_price,
        "position_value": p.position_value,
        "total_equity": p.total_equity,
        "event_signal_snapshot_id": p.event_signal_snapshot_id,
    }


def _trade_domain(row: BacktestTradeRow) -> Trade:
    return Trade(
        row.id,
        row.sequence,
        row.entry_signal_snapshot_id,
        row.exit_signal_snapshot_id,
        row.entry_time,
        row.exit_time,
        Decimal(row.entry_reference_price),
        Decimal(row.exit_reference_price),
        Decimal(row.entry_price),
        Decimal(row.exit_price),
        TradeSide(row.side),
        Decimal(row.quantity),
        Decimal(row.entry_fee),
        Decimal(row.exit_fee),
        Decimal(row.profit_loss),
        Decimal(row.return_percent),
        CloseReason(row.close_reason),
    )


def _equity_domain(row: BacktestEquityPointRow) -> EquityPoint:
    return EquityPoint(
        row.id,
        row.position,
        row.candle_open_time,
        row.valued_at,
        Decimal(row.cash),
        Decimal(row.quantity),
        Decimal(row.close_price),
        Decimal(row.position_value),
        Decimal(row.total_equity),
        row.event_signal_snapshot_id,
    )


async def _load_result(session: AsyncSession, row: BacktestResultRow) -> BacktestResult:
    run_row = await session.get(BacktestRunRow, row.run_id)
    if run_row is None:
        raise RuntimeError("backtest run provenance is missing")
    signal_rows = (
        await session.scalars(
            select(BacktestSignalSnapshotRow)
            .where(BacktestSignalSnapshotRow.backtest_result_id == row.id)
            .order_by(BacktestSignalSnapshotRow.sequence)
        )
    ).all()
    trade_rows = (
        await session.scalars(
            select(BacktestTradeRow)
            .where(BacktestTradeRow.backtest_result_id == row.id)
            .order_by(BacktestTradeRow.sequence)
        )
    ).all()
    equity_rows = (
        await session.scalars(
            select(BacktestEquityPointRow)
            .where(BacktestEquityPointRow.backtest_result_id == row.id)
            .order_by(BacktestEquityPointRow.position)
        )
    ).all()
    snapshots = []
    for item in signal_rows:
        reason, no_op = item.reason, None
        if reason and reason.startswith("NOOP:"):
            head, _, tail = reason.partition("|")
            no_op, reason = NoOpCode(head.removeprefix("NOOP:")), tail or None
        snapshots.append(
            SignalSnapshot(
                item.id,
                item.source_signal_id,
                item.sequence,
                item.timestamp,
                item.action,
                item.phase,
                None if item.strength is None else Decimal(item.strength),
                reason,
                no_op,
            )
        )
    return BacktestResult(
        row.id,
        _run_domain(run_row).configuration,
        row.result_checksum,
        BacktestHistoryState(row.history_state),
        TradeState(row.trade_state),
        tuple(snapshots),
        tuple(_trade_domain(item) for item in trade_rows),
        EquityCurve(tuple(_equity_domain(item) for item in equity_rows)),
        row.execution_duration_ms,
        row.created_at,
    )
