"""Immutable identity of sentiment evidence used by a strategy analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SentimentProvenance:
    model_id: str
    model_version: str
    window_start: datetime
    window_end: datetime
    evidence_fingerprint: str

    def to_payload(self) -> dict[str, str]:
        return {
            "modelId": self.model_id,
            "modelVersion": self.model_version,
            "windowStart": self.window_start.isoformat(),
            "windowEnd": self.window_end.isoformat(),
            "evidenceFingerprint": self.evidence_fingerprint,
        }

    @classmethod
    def from_payload(cls, value: dict[str, Any]) -> SentimentProvenance:
        return cls(
            value["modelId"],
            value["modelVersion"],
            datetime.fromisoformat(value["windowStart"]),
            datetime.fromisoformat(value["windowEnd"]),
            value["evidenceFingerprint"],
        )
