"""Model identity and vocabulary shared by every sentiment analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SentimentLabel(StrEnum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class SentimentStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ModelRef:
    """Identity of the exact model (and version) that produced an analysis."""

    model_id: str
    model_version: str

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("model_id must not be blank")
        if not self.model_version.strip():
            raise ValueError("model_version must not be blank")


__all__ = ["ModelRef", "SentimentLabel", "SentimentStatus"]
