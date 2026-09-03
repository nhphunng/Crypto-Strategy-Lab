from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from crypto_lab.domain.market_data.candle import Candle, format_utc_millis
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc
from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError


class ContextCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True, slots=True)
class StrategyContext:
    dataset_id: str
    dataset_version: str
    provider: str
    pair: str
    timeframe: Timeframe
    range_start: datetime
    range_end: datetime
    decision_timestamp: datetime
    completeness: ContextCompleteness
    candles: tuple[Candle, ...]
    evidence_fingerprint: str | None = None
    _context_fingerprint: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        issues: list[ErrorIssue] = []
        try:
            start = require_utc(self.range_start)
            end = require_utc(self.range_end)
            decision = require_utc(self.decision_timestamp)
        except ValueError as exc:
            raise StrategyError(ErrorCategory.INVALID_CONTEXT, str(exc)) from exc
        if not self.dataset_id or not self.dataset_version:
            issues.append(
                ErrorIssue("dataset", "REQUIRED", "dataset identity and version are required")
            )
        if start > end:
            issues.append(ErrorIssue("range", "INVALID", "range start must not exceed range end"))
        if self.completeness is not ContextCompleteness.COMPLETE:
            issues.append(ErrorIssue("completeness", "INCOMPLETE", "complete input is required"))
        previous: Candle | None = None
        for index, candle in enumerate(self.candles):
            if (candle.provider, candle.pair, candle.timeframe) != (
                self.provider,
                self.pair,
                self.timeframe,
            ):
                issues.append(
                    ErrorIssue(f"candles[{index}]", "MISALIGNED", "market selection differs")
                )
            if not candle.closed:
                issues.append(ErrorIssue(f"candles[{index}]", "OPEN", "candle must be closed"))
            if candle.close_time > decision:
                issues.append(
                    ErrorIssue(f"candles[{index}]", "FUTURE", "candle closes after decision")
                )
            if candle.open_time < start or candle.close_time > end:
                issues.append(
                    ErrorIssue(f"candles[{index}]", "OUTSIDE_RANGE", "candle is outside range")
                )
            if previous is not None:
                if candle.open_time <= previous.open_time:
                    issues.append(
                        ErrorIssue(
                            f"candles[{index}]",
                            "UNSORTED_OR_DUPLICATE",
                            "timestamps must strictly ascend",
                        )
                    )
                elif candle.open_time != previous.open_time + self.timeframe.duration:
                    issues.append(
                        ErrorIssue(
                            f"candles[{index}]", "GAP", "complete context cannot contain gaps"
                        )
                    )
            previous = candle
        if issues:
            raise StrategyError(
                ErrorCategory.INVALID_CONTEXT, "strategy context is invalid", tuple(issues)
            )
        object.__setattr__(self, "_context_fingerprint", self._calculate_fingerprint())

    @property
    def context_fingerprint(self) -> str:
        return self._context_fingerprint

    def _calculate_fingerprint(self) -> str:
        header = "|".join(
            (
                self.dataset_id,
                self.dataset_version,
                self.provider,
                self.pair,
                self.timeframe.value,
                format_utc_millis(self.range_start),
                format_utc_millis(self.range_end),
                format_utc_millis(self.decision_timestamp),
            )
        )
        body = "\n".join(candle.canonical_line() for candle in self.candles)
        if self.evidence_fingerprint is not None:
            body += f"\nevidence:{self.evidence_fingerprint}"
        return hashlib.sha256(f"{header}\n{body}".encode()).hexdigest()
