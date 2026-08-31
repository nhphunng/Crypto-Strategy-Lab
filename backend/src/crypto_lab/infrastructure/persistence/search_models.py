from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class StrategySearchRunRow(Base):
    __tablename__ = "strategy_search_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED')",
            name="ck_strategy_search_runs_status",
        ),
        Index("ix_strategy_search_runs_created", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("candle_datasets.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    minimum_size: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_size: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    no_improvement_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    seed: Mapped[int] = mapped_column(nullable=False)
    generator_id: Mapped[str] = mapped_column(String(64), nullable=False)
    generator_version: Mapped[str] = mapped_column(String(32), nullable=False)
    generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    running: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_score: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    top_candidate: Mapped[str | None] = mapped_column(String(512))
    current_candidate: Mapped[str | None] = mapped_column(String(512))
    stop_reason: Mapped[str | None] = mapped_column(String(64))
    failure_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StrategySearchCandidateRow(Base):
    __tablename__ = "strategy_search_candidates"
    __table_args__ = (
        Index("ix_strategy_search_candidates_run_score", "search_run_id", "score"),
        UniqueConstraint(
            "search_run_id",
            "fingerprint",
            name="uq_strategy_search_candidate_fingerprint",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    search_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_search_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    members: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    backtest_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="SET NULL")
    )
    evaluation_result_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("evaluation_results.id", ondelete="SET NULL")
    )
    failure_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
