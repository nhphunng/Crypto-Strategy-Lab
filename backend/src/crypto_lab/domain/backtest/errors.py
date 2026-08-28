from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BacktestErrorCode(StrEnum):
    CONFIGURATION_INVALID = "BACKTEST_CONFIGURATION_INVALID"
    DATASET_INELIGIBLE = "BACKTEST_DATASET_INELIGIBLE"
    DATASET_INTEGRITY_FAILED = "BACKTEST_DATASET_INTEGRITY_FAILED"
    STRATEGY_INCOMPATIBLE = "BACKTEST_STRATEGY_INCOMPATIBLE"
    SIGNAL_MISALIGNED = "BACKTEST_SIGNAL_MISALIGNED"
    INSUFFICIENT_CAPITAL = "BACKTEST_INSUFFICIENT_CAPITAL"
    JOB_CONFLICT = "BACKTEST_JOB_CONFLICT"
    EXECUTION_FAILED = "BACKTEST_EXECUTION_FAILED"


class NoOpCode(StrEnum):
    HOLD = "HOLD"
    WARMUP = "WARMUP"
    ALREADY_LONG = "ALREADY_LONG"
    ALREADY_FLAT = "ALREADY_FLAT"
    FINAL_CANDLE_SIGNAL = "FINAL_CANDLE_SIGNAL"
    INSUFFICIENT_CAPITAL = "INSUFFICIENT_CAPITAL"


@dataclass(frozen=True, slots=True)
class BacktestIssue:
    field: str
    code: str
    message: str


class BacktestError(Exception):
    def __init__(
        self,
        code: BacktestErrorCode,
        message: str,
        issues: tuple[BacktestIssue, ...] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.issues = issues
