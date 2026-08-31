"""Create deterministic backtest and evaluation storage.

Revision ID: 20260813_004_backtest
Revises: 20260813_003_strategy
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260813_004_backtest"
down_revision: str | None = "20260813_003_strategy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "execution_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(fingerprint) = 64",
            name="ck_execution_policies_fingerprint_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution_policies"),
        sa.UniqueConstraint("fingerprint", name="uq_execution_policies_fingerprint"),
        sa.UniqueConstraint("policy_id", "version", name="uq_execution_policies_identity"),
    )
    op.create_table(
        "evaluation_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(fingerprint) = 64",
            name="ck_evaluation_policies_fingerprint_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_policies"),
        sa.UniqueConstraint("fingerprint", name="uq_evaluation_policies_fingerprint"),
        sa.UniqueConstraint("policy_id", "version", name="uq_evaluation_policies_identity"),
    )
    op.create_table(
        "scoring_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("default_rank_metric", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(fingerprint) = 64",
            name="ck_scoring_policies_fingerprint_length",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scoring_policies"),
        sa.UniqueConstraint("fingerprint", name="uq_scoring_policies_fingerprint"),
        sa.UniqueConstraint("policy_id", "version", name="uq_scoring_policies_identity"),
    )
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_schema_version", sa.String(length=16), nullable=False),
        sa.Column("dataset_checksum", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("pair", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("contract_version", sa.String(length=32), nullable=False),
        sa.Column("parameter_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("context_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("execution_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_policy_version", sa.String(length=32), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("fee_rate", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("slippage_rate", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("random_seed", sa.BigInteger(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "length(context_fingerprint) = 64",
            name="ck_backtest_runs_context_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(dataset_checksum) = 64",
            name="ck_backtest_runs_dataset_checksum_length",
        ),
        sa.CheckConstraint("fee_rate >= 0", name="ck_backtest_runs_fee_rate"),
        sa.CheckConstraint("initial_capital > 0", name="ck_backtest_runs_initial_capital"),
        sa.CheckConstraint(
            "length(parameter_fingerprint) = 64",
            name="ck_backtest_runs_parameter_fingerprint_length",
        ),
        sa.CheckConstraint("slippage_rate >= 0", name="ck_backtest_runs_slippage_rate"),
        sa.CheckConstraint(
            "status IN ('REQUESTED','RUNNING','COMPLETED','FAILED')",
            name="ck_backtest_runs_status",
        ),
        sa.CheckConstraint("start_time < end_time", name="ck_backtest_runs_time_range"),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["candle_datasets.id"],
            name="fk_backtest_runs_dataset_id_candle_datasets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_policy_id"],
            ["execution_policies.id"],
            name="fk_backtest_runs_execution_policy_id_execution_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_definition_id"],
            ["strategy_definitions.id"],
            name="fk_backtest_runs_strategy_definition_id_strategy_definitions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_runs"),
        sa.UniqueConstraint("job_id", name="uq_backtest_runs_job_id"),
    )
    op.create_index(
        "ix_backtest_runs_dataset_status",
        "backtest_runs",
        ["dataset_id", "status"],
        unique=False,
    )
    op.create_table(
        "backtest_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("result_checksum", sa.String(length=64), nullable=False),
        sa.Column("history_state", sa.String(length=16), nullable=False),
        sa.Column("trade_state", sa.String(length=16), nullable=False),
        sa.Column("initial_capital", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("final_equity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False),
        sa.Column("trade_count", sa.Integer(), nullable=False),
        sa.Column("equity_point_count", sa.Integer(), nullable=False),
        sa.Column("execution_duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_checksum", sa.String(length=64), nullable=False),
        sa.Column("strategy_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_policy_version", sa.String(length=32), nullable=False),
        sa.Column("execution_config_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "signal_count >= 0 AND trade_count >= 0 AND equity_point_count >= 0",
            name="ck_backtest_results_child_counts",
        ),
        sa.CheckConstraint(
            "execution_duration_ms >= 0",
            name="ck_backtest_results_execution_duration",
        ),
        sa.CheckConstraint("final_equity >= 0", name="ck_backtest_results_final_equity"),
        sa.CheckConstraint(
            "length(input_fingerprint) = 64 AND length(result_checksum) = 64",
            name="ck_backtest_results_hash_lengths",
        ),
        sa.CheckConstraint(
            "history_state IN ('INSUFFICIENT','EVALUABLE')",
            name="ck_backtest_results_history_state",
        ),
        sa.CheckConstraint("initial_capital > 0", name="ck_backtest_results_initial_capital"),
        sa.CheckConstraint(
            "length(dataset_checksum) = 64 AND length(execution_config_fingerprint) = 64",
            name="ck_backtest_results_provenance_hash_lengths",
        ),
        sa.CheckConstraint(
            "trade_state IN ('NO_TRADES','HAS_TRADES')",
            name="ck_backtest_results_trade_state",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["candle_datasets.id"],
            name="fk_backtest_results_dataset_id_candle_datasets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_policy_id"],
            ["execution_policies.id"],
            name="fk_backtest_results_execution_policy_id_execution_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["backtest_runs.id"],
            name="fk_backtest_results_run_id_backtest_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_definition_id"],
            ["strategy_definitions.id"],
            name="fk_backtest_results_strategy_definition_id_strategy_definitions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_results"),
        sa.UniqueConstraint("input_fingerprint", name="uq_backtest_results_input_fingerprint"),
        sa.UniqueConstraint("job_id", name="uq_backtest_results_job_id"),
        sa.UniqueConstraint("result_checksum", name="uq_backtest_results_result_checksum"),
        sa.UniqueConstraint("run_id", name="uq_backtest_results_run_id"),
    )
    op.create_index(
        "ix_backtest_results_input_fingerprint",
        "backtest_results",
        ["input_fingerprint"],
        unique=False,
    )
    op.create_table(
        "backtest_signal_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_signal_id", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(length=8), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("strength", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("strategy_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("contract_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_schema_version", sa.String(length=16), nullable=False),
        sa.Column("dataset_checksum", sa.String(length=64), nullable=False),
        sa.Column("analysis_result_fingerprint", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "action IN ('BUY','SELL','HOLD')",
            name="ck_backtest_signal_snapshots_action",
        ),
        sa.CheckConstraint(
            "length(dataset_checksum) = 64 AND length(analysis_result_fingerprint) = 64",
            name="ck_backtest_signal_snapshots_hash_lengths",
        ),
        sa.CheckConstraint(
            "phase IN ('WARMUP','EVALUATED')",
            name="ck_backtest_signal_snapshots_phase",
        ),
        sa.CheckConstraint("sequence >= 0", name="ck_backtest_signal_snapshots_sequence"),
        sa.ForeignKeyConstraint(
            ["backtest_result_id"],
            ["backtest_results.id"],
            name="fk_backtest_signal_snapshots_result_id_backtest_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["candle_datasets.id"],
            name="fk_backtest_signal_snapshots_dataset_id_candle_datasets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_definition_id"],
            ["strategy_definitions.id"],
            name="fk_backtest_signal_snapshots_strategy_id_strategy_definitions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_signal_snapshots"),
        sa.UniqueConstraint(
            "backtest_result_id",
            "sequence",
            name="uq_backtest_signal_snapshots_sequence",
        ),
        sa.UniqueConstraint(
            "backtest_result_id",
            "source_signal_id",
            name="uq_backtest_signal_snapshots_source_signal",
        ),
    )
    op.create_index(
        "ix_backtest_signal_snapshots_result_sequence",
        "backtest_signal_snapshots",
        ["backtest_result_id", "sequence"],
        unique=False,
    )
    op.create_table(
        "backtest_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("entry_signal_snapshot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("exit_signal_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_reference_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("exit_reference_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("exit_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("entry_fee", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("exit_fee", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("profit_loss", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("return_percent", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("close_reason", sa.String(length=24), nullable=False),
        sa.CheckConstraint(
            "close_reason IN ('SELL_SIGNAL','END_OF_RANGE')",
            name="ck_backtest_trades_close_reason",
        ),
        sa.CheckConstraint(
            "entry_fee >= 0 AND exit_fee >= 0",
            name="ck_backtest_trades_fees_non_negative",
        ),
        sa.CheckConstraint(
            "entry_reference_price > 0 AND exit_reference_price > 0 "
            "AND entry_price > 0 AND exit_price > 0",
            name="ck_backtest_trades_prices_positive",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_backtest_trades_quantity_positive"),
        sa.CheckConstraint("sequence >= 0", name="ck_backtest_trades_sequence"),
        sa.CheckConstraint("side = 'LONG'", name="ck_backtest_trades_side"),
        sa.CheckConstraint("entry_time <= exit_time", name="ck_backtest_trades_time_order"),
        sa.ForeignKeyConstraint(
            ["backtest_result_id"],
            ["backtest_results.id"],
            name="fk_backtest_trades_result_id_backtest_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["entry_signal_snapshot_id"],
            ["backtest_signal_snapshots.id"],
            name="fk_backtest_trades_entry_signal_signal_snapshots",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["exit_signal_snapshot_id"],
            ["backtest_signal_snapshots.id"],
            name="fk_backtest_trades_exit_signal_signal_snapshots",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_trades"),
        sa.UniqueConstraint("backtest_result_id", "sequence", name="uq_backtest_trades_sequence"),
    )
    op.create_index(
        "ix_backtest_trades_result_sequence",
        "backtest_trades",
        ["backtest_result_id", "sequence"],
        unique=False,
    )
    op.create_table(
        "backtest_equity_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("candle_open_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("close_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("position_value", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("total_equity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("event_signal_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("position >= 0", name="ck_backtest_equity_points_position"),
        sa.CheckConstraint(
            "cash >= 0 AND quantity >= 0 AND close_price > 0 "
            "AND position_value >= 0 AND total_equity >= 0",
            name="ck_backtest_equity_points_values",
        ),
        sa.ForeignKeyConstraint(
            ["backtest_result_id"],
            ["backtest_results.id"],
            name="fk_backtest_equity_points_result_id_backtest_results",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_signal_snapshot_id"],
            ["backtest_signal_snapshots.id"],
            name="fk_backtest_equity_points_event_signal_signal_snapshots",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_backtest_equity_points"),
        sa.UniqueConstraint(
            "backtest_result_id",
            "position",
            name="uq_backtest_equity_points_position",
        ),
    )
    op.create_index(
        "ix_backtest_equity_points_result_position",
        "backtest_equity_points",
        ["backtest_result_id", "position"],
        unique=False,
    )
    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backtest_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_checksum", sa.String(length=64), nullable=False),
        sa.Column("pair", sa.String(length=20), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_policy_version", sa.String(length=32), nullable=False),
        sa.Column("execution_config_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "execution_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("evaluation_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_policy_version", sa.String(length=32), nullable=False),
        sa.Column("scoring_policy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scoring_policy_version", sa.String(length=32), nullable=False),
        sa.Column("total_return", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("win_rate", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("max_drawdown", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("number_of_trades", sa.Integer(), nullable=False),
        sa.Column("profit_factor", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("score", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.Column(
            "exclusion_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(dataset_checksum) = 64 "
            "AND length(execution_config_fingerprint) = 64 "
            "AND length(content_fingerprint) = 64",
            name="ck_evaluation_results_hash_lengths",
        ),
        sa.CheckConstraint(
            "number_of_trades >= 0",
            name="ck_evaluation_results_trade_count",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_evaluation_results_score_range",
        ),
        sa.CheckConstraint(
            "start_time < end_time",
            name="ck_evaluation_results_time_range",
        ),
        sa.ForeignKeyConstraint(
            ["backtest_result_id"],
            ["backtest_results.id"],
            name="fk_evaluation_results_result_id_backtest_results",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["candle_datasets.id"],
            name="fk_evaluation_results_dataset_id_candle_datasets",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_policy_id"],
            ["evaluation_policies.id"],
            name="fk_evaluation_results_policy_id_evaluation_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["execution_policy_id"],
            ["execution_policies.id"],
            name="fk_evaluation_results_execution_policy_id_execution_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["backtest_runs.id"],
            name="fk_evaluation_results_run_id_backtest_runs",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scoring_policy_id"],
            ["scoring_policies.id"],
            name="fk_evaluation_results_policy_id_scoring_policies",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_definition_id"],
            ["strategy_definitions.id"],
            name="fk_evaluation_results_strategy_id_strategy_definitions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_results"),
        sa.UniqueConstraint(
            "content_fingerprint",
            name="uq_evaluation_results_fingerprint",
        ),
        sa.UniqueConstraint(
            "backtest_result_id",
            "evaluation_policy_id",
            "evaluation_policy_version",
            "scoring_policy_id",
            "scoring_policy_version",
            name="uq_evaluation_results_source_policies",
        ),
    )
    op.create_index(
        "ix_evaluation_results_backtest_result",
        "evaluation_results",
        ["backtest_result_id"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_results_comparison",
        "evaluation_results",
        ["dataset_id", "strategy_id", "strategy_version", "pair", "timeframe"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_comparison", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_backtest_result", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_index(
        "ix_backtest_equity_points_result_position",
        table_name="backtest_equity_points",
    )
    op.drop_table("backtest_equity_points")
    op.drop_index("ix_backtest_trades_result_sequence", table_name="backtest_trades")
    op.drop_table("backtest_trades")
    op.drop_index(
        "ix_backtest_signal_snapshots_result_sequence",
        table_name="backtest_signal_snapshots",
    )
    op.drop_table("backtest_signal_snapshots")
    op.drop_index("ix_backtest_results_input_fingerprint", table_name="backtest_results")
    op.drop_table("backtest_results")
    op.drop_index("ix_backtest_runs_dataset_status", table_name="backtest_runs")
    op.drop_table("backtest_runs")
    op.drop_table("scoring_policies")
    op.drop_table("evaluation_policies")
    op.drop_table("execution_policies")
