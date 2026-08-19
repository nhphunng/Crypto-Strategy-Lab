"""SQLAlchemy mappings for immutable evaluation records using the shared Base."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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


class EvaluationPolicyRow(Base):
    __tablename__ = "evaluation_policies"
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_evaluation_policies_identity"),
        UniqueConstraint("fingerprint", name="uq_evaluation_policies_fingerprint"),
        CheckConstraint(
            "length(fingerprint) = 64",
            name="ck_evaluation_policies_fingerprint_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    rules: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScoringPolicyRow(Base):
    __tablename__ = "scoring_policies"
    __table_args__ = (
        UniqueConstraint("policy_id", "version", name="uq_scoring_policies_identity"),
        UniqueConstraint("fingerprint", name="uq_scoring_policies_fingerprint"),
        CheckConstraint(
            "length(fingerprint) = 64",
            name="ck_scoring_policies_fingerprint_length",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    default_rank_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    rules: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvaluationResultRow(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        UniqueConstraint(
            "backtest_result_id",
            "evaluation_policy_id",
            "evaluation_policy_version",
            "scoring_policy_id",
            "scoring_policy_version",
            name="uq_evaluation_results_source_policies",
        ),
        UniqueConstraint("content_fingerprint", name="uq_evaluation_results_fingerprint"),
        CheckConstraint("start_time < end_time", name="ck_evaluation_results_time_range"),
        CheckConstraint("number_of_trades >= 0", name="ck_evaluation_results_trade_count"),
        CheckConstraint(
            "score >= 0 AND score <= 100",
            name="ck_evaluation_results_score_range",
        ),
        CheckConstraint(
            "length(dataset_checksum) = 64 "
            "AND length(execution_config_fingerprint) = 64 "
            "AND length(content_fingerprint) = 64",
            name="ck_evaluation_results_hash_lengths",
        ),
        Index("ix_evaluation_results_backtest_result", "backtest_result_id"),
        Index(
            "ix_evaluation_results_comparison",
            "dataset_id",
            "strategy_id",
            "strategy_version",
            "pair",
            "timeframe",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    backtest_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_results.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("candle_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    execution_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("execution_policies.id", ondelete="RESTRICT"), nullable=False
    )
    execution_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    execution_config_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_config: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    evaluation_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("evaluation_policies.id", ondelete="RESTRICT"), nullable=False
    )
    evaluation_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scoring_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("scoring_policies.id", ondelete="RESTRICT"), nullable=False
    )
    scoring_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    win_rate: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    number_of_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    profit_factor: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(38, 18))
    score: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    eligible: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exclusion_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
