from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.strategy.generation import GenerationSourceType


class RetentionClass(StrEnum):
    RAW_30_DAY_MAX = "RAW_30_DAY_MAX"
    FINGERPRINT_ONLY = "FINGERPRINT_ONLY"


@dataclass(frozen=True, slots=True)
class StrategySourceSnapshot:
    id: UUID
    source_type: GenerationSourceType
    content_fingerprint: str
    access_policy_version: str
    retention_class: RetentionClass
    submitted_url: str | None = None
    canonical_url: str | None = None
    title: str | None = None
    attribution: str | None = None
    retrieved_at: datetime | None = None
    encrypted_content: bytes | None = None
    encryption_key_id: str | None = None
    media_type: str | None = None
    size: int | None = None
    raw_content_expires_at: datetime | None = None
    raw_content_purged_at: datetime | None = None

    @classmethod
    def fingerprint(cls, content: str) -> str:
        return hashlib.sha256(content.replace("\r\n", "\n").encode()).hexdigest()

    def __post_init__(self) -> None:
        if len(self.content_fingerprint) != 64:
            raise ValueError("source fingerprint must be SHA-256")
        protected = self.encrypted_content is not None
        if protected != (self.encryption_key_id is not None):
            raise ValueError("encrypted content and key ID must be present together")
        if protected and self.raw_content_expires_at is None:
            raise ValueError("protected raw content requires an expiry")


@dataclass(frozen=True, slots=True)
class StrategyGenerationProvenance:
    id: UUID
    request_id: UUID
    source_snapshot_id: UUID
    draft_id: UUID
    artifact_id: UUID
    validation_report_id: UUID
    strategy_id: str
    strategy_version: str
    model_provider: str
    model_id: str
    model_version: str
    prompt_template_version: str
    generated_at: datetime
    confirmed_at: datetime
    confirmed_by: str
    activation_policy_version: str
