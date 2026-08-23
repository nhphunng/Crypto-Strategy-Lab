"""Immutable Strategy Definition mappings owned by Feature 003."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from crypto_lab.infrastructure.persistence.models import Base


class StrategyDefinitionRow(Base):
    __tablename__ = "strategy_definitions"
    __table_args__ = (
        UniqueConstraint(
            "content_fingerprint",
            name="uq_strategy_definitions_content_fingerprint",
        ),
        CheckConstraint(
            "length(parameter_schema_fingerprint) = 64",
            name="ck_strategy_definitions_parameter_schema_fingerprint_length",
        ),
        CheckConstraint(
            "length(content_fingerprint) = 64",
            name="ck_strategy_definitions_content_fingerprint_length",
        ),
        Index(
            "ix_strategy_definitions_strategy_version",
            "strategy_id",
            "strategy_version",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(32), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(32), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(32), nullable=False)
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    parameter_schema_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, default="BUILT_IN")
    generated_artifact_id: Mapped[UUID | None] = mapped_column(nullable=True)
    generation_provenance_id: Mapped[UUID | None] = mapped_column(nullable=True)
