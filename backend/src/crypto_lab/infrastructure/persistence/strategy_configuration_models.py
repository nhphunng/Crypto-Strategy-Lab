from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class SavedStrategyConfigurationRow(Base):
    __tablename__ = "saved_strategy_configurations"
    __table_args__ = (
        UniqueConstraint(
            "configuration_key",
            "configuration_version",
            name="uq_saved_strategy_configurations_key_version",
        ),
        UniqueConstraint(
            "content_fingerprint",
            name="uq_saved_strategy_configurations_content_fingerprint",
        ),
        Index("ix_saved_strategy_configurations_created", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    configuration_key: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_version: Mapped[int] = mapped_column(Integer, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    root_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    pair: Mapped[str] = mapped_column(String(32), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    combination: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavedStrategyConfigurationMemberRow(Base):
    __tablename__ = "saved_strategy_configuration_members"

    configuration_id: Mapped[UUID] = mapped_column(
        ForeignKey("saved_strategy_configurations.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("strategy_definitions.id", ondelete="RESTRICT"), nullable=False
    )
    definition_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    weight: Mapped[str | None] = mapped_column(String(64), nullable=True)
