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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CandleRow(Base):
    __tablename__ = "candles"
    __table_args__ = (
        UniqueConstraint("provider", "pair", "timeframe", "open_time", name="uq_candles_identity"),
        CheckConstraint(
            "open > 0 AND high > 0 AND low > 0 AND close > 0", name="ck_candles_prices_positive"
        ),
        CheckConstraint("volume >= 0", name="ck_candles_volume_non_negative"),
        CheckConstraint("high >= open AND high >= low AND high >= close", name="ck_candles_high"),
        CheckConstraint("low <= open AND low <= high AND low <= close", name="ck_candles_low"),
        CheckConstraint("closed = true", name="ck_candles_historical_closed"),
        Index("ix_candles_selection_open", "provider", "pair", "timeframe", "open_time"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(38, 18), nullable=False)
    closed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CandleDatasetRow(Base):
    __tablename__ = "candle_datasets"
    __table_args__ = (
        UniqueConstraint("request_key", name="uq_candle_datasets_request_key"),
        UniqueConstraint(
            "schema_version",
            "provider",
            "pair",
            "timeframe",
            "start_time",
            "end_time",
            name="uq_candle_datasets_selection_range",
        ),
        CheckConstraint(
            "status IN ('BUILDING','COMPLETE','INCOMPLETE','FAILED')",
            name="ck_candle_datasets_status",
        ),
        CheckConstraint(
            "(status <> 'COMPLETE') OR "
            "(candle_count > 0 AND checksum IS NOT NULL AND completed_at IS NOT NULL "
            "AND build_token IS NULL AND lease_expires_at IS NULL)",
            name="ck_candle_datasets_complete_fields",
        ),
        CheckConstraint(
            "(status <> 'BUILDING') OR (build_token IS NOT NULL AND lease_expires_at IS NOT NULL)",
            name="ck_candle_datasets_build_fields",
        ),
        Index("ix_candle_datasets_status_lease", "status", "lease_expires_at"),
        Index(
            "ix_candle_datasets_selection_range",
            "provider",
            "pair",
            "timeframe",
            "start_time",
            "end_time",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    pair: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    candle_count: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))
    build_token: Mapped[UUID | None] = mapped_column()
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    members: Mapped[list[CandleDatasetMemberRow]] = relationship(
        back_populates="dataset", order_by="CandleDatasetMemberRow.position"
    )


class CandleDatasetMemberRow(Base):
    __tablename__ = "candle_dataset_members"
    __table_args__ = (
        UniqueConstraint("dataset_id", "candle_id", name="uq_dataset_member_candle"),
        CheckConstraint("position >= 0", name="ck_dataset_member_position"),
    )

    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("candle_datasets.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    candle_id: Mapped[UUID] = mapped_column(
        ForeignKey("candles.id", ondelete="RESTRICT"), nullable=False
    )
    dataset: Mapped[CandleDatasetRow] = relationship(back_populates="members")
    candle: Mapped[CandleRow] = relationship()
