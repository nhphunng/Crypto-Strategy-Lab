"""SQLAlchemy mappings for append-only backtest records using the shared Base."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class ExecutionPolicyRow(Base):
    __tablename__ = "execution_policies"
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_execution_policies_identity"),
        UniqueConstraint("fingerprint", name="uq_execution_policies_fingerprint"),
        CheckConstraint(
            "length(fingerprint) = 64",
            name="ck_execution_policies_fingerprint_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    rules: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestRunRow(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_backtest_runs_job_id"),
        CheckConstraint(
            "status IN ('REQUESTED','RUNNING','COMPLETED','FAILED')",
            name="ck_backtest_runs_status",
        ),
        CheckConstraint("start_time < end_time", name="ck_backtest_runs_time_range"),
        CheckConstraint("initial_capital > 0", name="ck_backtest_runs_initial_capital"),
        CheckConstraint("fee_rate >= 0", name="ck_backtest_runs_fee_rate"),
        CheckConstraint("slippage_rate >= 0", name="ck_backtest_runs_slippage_rate"),
        CheckConstraint(
            "length(dataset_checksum) = 64",
            name="ck_backtest_runs_dataset_checksum_length",
        ),
        CheckConstraint(
            "length(parameter_fingerprint) = 64",
            name="ck_backtest_runs_parameter_fingerprint_length",
        ),
        CheckConstraint(
            "length(context_fingerprint) = 64",
            name="ck_backtest_runs_context_fingerprint_length",
        ),
        Index("ix_backtest_runs_dataset_status", "dataset_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("candle_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strategy_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    parameter_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    context_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_policies.id", ondelete="RESTRICT"), nullable=False
    )
    execution_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    fee_rate: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    slippage_rate: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    random_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(64))


class BacktestResultRow(Base):
    __tablename__ = "backtest_results"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_backtest_results_run_id"),
        UniqueConstraint("job_id", name="uq_backtest_results_job_id"),
        UniqueConstraint("input_fingerprint", name="uq_backtest_results_input_fingerprint"),
        UniqueConstraint("result_checksum", name="uq_backtest_results_result_checksum"),
        CheckConstraint(
            "history_state IN ('INSUFFICIENT','EVALUABLE')",
            name="ck_backtest_results_history_state",
        ),
        CheckConstraint(
            "trade_state IN ('NO_TRADES','HAS_TRADES')",
            name="ck_backtest_results_trade_state",
        ),
        CheckConstraint("initial_capital > 0", name="ck_backtest_results_initial_capital"),
        CheckConstraint("final_equity >= 0", name="ck_backtest_results_final_equity"),
        CheckConstraint(
            "signal_count >= 0 AND trade_count >= 0 AND equity_point_count >= 0",
            name="ck_backtest_results_child_counts",
        ),
        CheckConstraint(
            "execution_duration_ms >= 0",
            name="ck_backtest_results_execution_duration",
        ),
        CheckConstraint(
            "length(input_fingerprint) = 64 AND length(result_checksum) = 64",
            name="ck_backtest_results_hash_lengths",
        ),
        CheckConstraint(
            "length(dataset_checksum) = 64 AND length(execution_config_fingerprint) = 64",
            name="ck_backtest_results_provenance_hash_lengths",
        ),
        Index("ix_backtest_results_input_fingerprint", "input_fingerprint"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    result_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    history_state: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_state: Mapped[str] = mapped_column(String(16), nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    final_equity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    signal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False)
    equity_point_count: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("candle_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    execution_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_policies.id", ondelete="RESTRICT"), nullable=False
    )
    execution_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_config_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BacktestSignalSnapshotRow(Base):
    __tablename__ = "backtest_signal_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "backtest_result_id",
            "sequence",
            name="uq_backtest_signal_snapshots_sequence",
        ),
        UniqueConstraint(
            "backtest_result_id",
            "source_signal_id",
            name="uq_backtest_signal_snapshots_source_signal",
        ),
        CheckConstraint("sequence >= 0", name="ck_backtest_signal_snapshots_sequence"),
        CheckConstraint(
            "action IN ('BUY','SELL','HOLD')",
            name="ck_backtest_signal_snapshots_action",
        ),
        CheckConstraint(
            "phase IN ('WARMUP','EVALUATED')",
            name="ck_backtest_signal_snapshots_phase",
        ),
        CheckConstraint(
            "length(dataset_checksum) = 64 AND length(analysis_result_fingerprint) = 64",
            name="ck_backtest_signal_snapshots_hash_lengths",
        ),
        Index(
            "ix_backtest_signal_snapshots_result_sequence",
            "backtest_result_id",
            "sequence",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    backtest_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_results.id", ondelete="CASCADE"), nullable=False
    )
    source_signal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    action: Mapped[str] = mapped_column(String(8), nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    strength: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    reason: Mapped[str | None] = mapped_column(String(256))
    strategy_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("candle_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_result_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class BacktestTradeRow(Base):
    __tablename__ = "backtest_trades"
    __table_args__ = (
        UniqueConstraint("backtest_result_id", "sequence", name="uq_backtest_trades_sequence"),
        CheckConstraint("sequence >= 0", name="ck_backtest_trades_sequence"),
        CheckConstraint("entry_time <= exit_time", name="ck_backtest_trades_time_order"),
        CheckConstraint(
            "entry_reference_price > 0 AND exit_reference_price > 0 "
            "AND entry_price > 0 AND exit_price > 0",
            name="ck_backtest_trades_prices_positive",
        ),
        CheckConstraint("quantity > 0", name="ck_backtest_trades_quantity_positive"),
        CheckConstraint(
            "entry_fee >= 0 AND exit_fee >= 0",
            name="ck_backtest_trades_fees_non_negative",
        ),
        CheckConstraint("side = 'LONG'", name="ck_backtest_trades_side"),
        CheckConstraint(
            "close_reason IN ('SELL_SIGNAL','END_OF_RANGE')",
            name="ck_backtest_trades_close_reason",
        ),
        Index("ix_backtest_trades_result_sequence", "backtest_result_id", "sequence"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    backtest_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_results.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_signal_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_signal_snapshots.id", ondelete="RESTRICT"), nullable=False
    )
    exit_signal_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("backtest_signal_snapshots.id", ondelete="RESTRICT")
    )
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_reference_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    exit_reference_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    exit_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    entry_fee: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    exit_fee: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    profit_loss: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    return_percent: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close_reason: Mapped[str] = mapped_column(String(24), nullable=False)


class BacktestEquityPointRow(Base):
    __tablename__ = "backtest_equity_points"
    __table_args__ = (
        UniqueConstraint(
            "backtest_result_id",
            "position",
            name="uq_backtest_equity_points_position",
        ),
        CheckConstraint("position >= 0", name="ck_backtest_equity_points_position"),
        CheckConstraint(
            "cash >= 0 AND quantity >= 0 AND close_price > 0 "
            "AND position_value >= 0 AND total_equity >= 0",
            name="ck_backtest_equity_points_values",
        ),
        Index(
            "ix_backtest_equity_points_result_position",
            "backtest_result_id",
            "position",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    backtest_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_results.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    candle_open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    position_value: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    event_signal_snapshot_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("backtest_signal_snapshots.id", ondelete="RESTRICT")
    )
