"""Feature 005 SQLAlchemy mappings for durable leaderboard projections."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class LeaderboardRow(Base):
    __tablename__ = "leaderboards"
    __table_args__ = (
        UniqueConstraint(
            "scope_key",
            "scoring_policy_id",
            "scoring_policy_version",
            "rank_metric",
            "k",
            name="uq_leaderboards_identity",
        ),
        CheckConstraint("k >= 1 AND k <= 200", name="ck_leaderboards_k_range"),
        CheckConstraint(
            "projection_version >= 0",
            name="ck_leaderboards_projection_version",
        ),
        CheckConstraint(
            "entry_count >= 0 AND entry_count <= k",
            name="ck_leaderboards_entry_count",
        ),
        CheckConstraint(
            "rank_metric IN "
            "('OVERALL_SCORE','TOTAL_RETURN','WIN_RATE','MAX_DRAWDOWN','SHARPE_RATIO')",
            name="ck_leaderboards_rank_metric",
        ),
        Index("ix_leaderboards_updated_at", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    scope_key: Mapped[str] = mapped_column(String(512), nullable=False)
    scoring_policy_id: Mapped[UUID] = mapped_column(
        ForeignKey("scoring_policies.id", ondelete="RESTRICT"), nullable=False
    )
    scoring_policy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    rank_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    k: Mapped[int] = mapped_column(Integer, nullable=False)
    projection_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="RESTRICT")
    )
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False)


class LeaderboardEntryRow(Base):
    __tablename__ = "leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("leaderboard_id", "rank", name="uq_leaderboard_entries_rank"),
        UniqueConstraint(
            "leaderboard_id",
            "evaluation_result_id",
            name="uq_leaderboard_entries_evaluation_result",
        ),
        CheckConstraint("rank > 0", name="ck_leaderboard_entries_rank"),
        CheckConstraint(
            "projection_version >= 0",
            name="ck_leaderboard_entries_projection_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    leaderboard_id: Mapped[UUID] = mapped_column(
        ForeignKey("leaderboards.id", ondelete="CASCADE"), nullable=False
    )
    evaluation_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("evaluation_results.id", ondelete="RESTRICT"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_key: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    projection_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LeaderboardUpdateRecordRow(Base):
    __tablename__ = "leaderboard_update_records"
    __table_args__ = (
        UniqueConstraint(
            "leaderboard_id",
            "projection_version",
            name="uq_leaderboard_update_records_projection_version",
        ),
        CheckConstraint(
            "projection_version > 0",
            name="ck_leaderboard_update_records_projection_version",
        ),
        CheckConstraint(
            "event_type = 'LEADERBOARD_UPDATED'",
            name="ck_leaderboard_update_records_event_type",
        ),
        Index(
            "ix_leaderboard_update_records_publication",
            "published_at",
            "occurred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    leaderboard_id: Mapped[UUID] = mapped_column(
        ForeignKey("leaderboards.id", ondelete="CASCADE"), nullable=False
    )
    projection_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_evaluation_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("evaluation_results.id", ondelete="RESTRICT"), nullable=False
    )
    source_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="RESTRICT")
    )
    source_job_id: Mapped[UUID | None] = mapped_column()
    added_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    removed_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    moved_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
