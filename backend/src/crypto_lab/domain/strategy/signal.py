from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.market_data.candle import format_utc_millis
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc
from crypto_lab.domain.sentiment.provenance import SentimentProvenance
from crypto_lab.domain.strategy.definition import StrategyDefinition
from crypto_lab.domain.strategy.parameters import ValidatedParameterSet
from crypto_lab.domain.strategy.version import SemanticVersion


class SignalAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalPhase(StrEnum):
    WARMUP = "WARMUP"
    EVALUATED = "EVALUATED"


class HistoryState(StrEnum):
    EMPTY = "EMPTY"
    INSUFFICIENT = "INSUFFICIENT"
    EVALUABLE = "EVALUABLE"


@dataclass(frozen=True, slots=True)
class Signal:
    id: str
    strategy_definition_id: UUID
    strategy_id: str
    strategy_type: str
    strategy_version: SemanticVersion
    contract_version: SemanticVersion
    dataset_id: str
    dataset_version: str
    timestamp: datetime
    sequence: int
    action: SignalAction
    phase: SignalPhase
    strength: Decimal | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        require_utc(self.timestamp)
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if self.strength is not None and not self.strength.is_finite():
            raise ValueError("strength must be finite")

    @classmethod
    def create(cls, *, context_fingerprint: str, **values: object) -> Signal:
        definition_id = values["strategy_definition_id"]
        timestamp = values["timestamp"]
        sequence = values["sequence"]
        if not isinstance(timestamp, datetime):
            raise TypeError("timestamp must be datetime")
        identity = (
            f"{definition_id}|{context_fingerprint}|{format_utc_millis(timestamp)}|{sequence}"
        )
        return cls(id=hashlib.sha256(identity.encode()).hexdigest(), **values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ContextProvenance:
    dataset_id: str
    dataset_version: str
    context_fingerprint: str
    provider: str
    pair: str
    timeframe: Timeframe
    range_start: datetime
    range_end: datetime
    decision_timestamp: datetime
    sentiment: tuple[SentimentProvenance, ...] = ()


@dataclass(frozen=True, slots=True)
class StrategyAnalysisResult:
    strategy_definition: StrategyDefinition
    validated_parameters: ValidatedParameterSet
    context_provenance: ContextProvenance
    contract_version: SemanticVersion
    history_state: HistoryState
    signals: tuple[Signal, ...]

    def __post_init__(self) -> None:
        if any(signal.sequence != index for index, signal in enumerate(self.signals)):
            raise ValueError("signal sequence must be contiguous")
        if (
            tuple(sorted(self.signals, key=lambda item: (item.timestamp, item.sequence)))
            != self.signals
        ):
            raise ValueError("signals must be deterministically ordered")
