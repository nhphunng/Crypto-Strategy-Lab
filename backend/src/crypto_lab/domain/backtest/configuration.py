from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal
from enum import StrEnum
from uuid import UUID

from crypto_lab.domain.backtest.errors import BacktestError, BacktestErrorCode, BacktestIssue
from crypto_lab.domain.market_data.candle import canonical_decimal, exact_decimal, format_utc_millis
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc
from crypto_lab.domain.sentiment.provenance import SentimentProvenance

DECIMAL_QUANTUM = Decimal("0.000000000000000001")


def quantity_decimal(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_QUANTUM, rounding=ROUND_DOWN)


def published_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("published decimal must be finite")
    return value.quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_EVEN)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


class RunStatus(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    id: UUID
    policy_id: str
    version: str
    signal_timing: str = "NEXT_CANDLE_OPEN"
    position_model: str = "LONG_ONLY"
    max_positions: int = 1
    sizing: str = "ALL_AVAILABLE_CASH"
    final_close: str = "FORCE_CLOSE_FINAL_CANDLE"
    quantity_precision: int = 18
    money_precision: int = 18

    def __post_init__(self) -> None:
        if not self.policy_id or not self.version:
            raise ValueError("execution policy identity is required")
        if (
            self.signal_timing != "NEXT_CANDLE_OPEN"
            or self.position_model != "LONG_ONLY"
            or self.max_positions != 1
            or self.sizing != "ALL_AVAILABLE_CASH"
            or self.final_close != "FORCE_CLOSE_FINAL_CANDLE"
            or self.quantity_precision != 18
            or self.money_precision != 18
        ):
            raise ValueError("unsupported execution policy rules")

    @property
    def rules(self) -> dict[str, object]:
        return {
            "finalClose": self.final_close,
            "maxPositions": self.max_positions,
            "moneyPrecision": self.money_precision,
            "positionModel": self.position_model,
            "quantityPrecision": self.quantity_precision,
            "signalTiming": self.signal_timing,
            "sizing": self.sizing,
        }

    @property
    def fingerprint(self) -> str:
        return canonical_hash(
            {"policyId": self.policy_id, "rules": self.rules, "version": self.version}
        )


@dataclass(frozen=True, slots=True)
class BacktestConfiguration:
    run_id: UUID
    job_id: UUID
    dataset_id: UUID
    dataset_schema_version: str
    dataset_checksum: str
    provider: str
    pair: str
    timeframe: Timeframe
    start_time: datetime
    end_time: datetime
    strategy_definition_id: UUID
    strategy_id: str
    strategy_version: str
    contract_version: str
    parameter_fingerprint: str
    context_fingerprint: str
    execution_policy_id: UUID
    execution_policy_version: str
    initial_capital: Decimal
    fee_rate: Decimal
    slippage_rate: Decimal
    random_seed: int
    sentiment_provenance: tuple[SentimentProvenance, ...] = ()

    def __post_init__(self) -> None:
        issues: list[BacktestIssue] = []
        try:
            start = require_utc(self.start_time)
            end = require_utc(self.end_time)
        except ValueError as exc:
            issues.append(BacktestIssue("range", "UTC_REQUIRED", str(exc)))
            start, end = self.start_time, self.end_time
        capital = exact_decimal(self.initial_capital, field="initial_capital")
        fee = exact_decimal(self.fee_rate, field="fee_rate")
        slippage = exact_decimal(self.slippage_rate, field="slippage_rate")
        if start >= end:
            issues.append(BacktestIssue("range", "INVALID", "startTime must precede endTime"))
        if capital <= 0:
            issues.append(BacktestIssue("initialCapital", "POSITIVE_REQUIRED", "must be positive"))
        if fee < 0:
            issues.append(BacktestIssue("feeRate", "NON_NEGATIVE_REQUIRED", "must be non-negative"))
        if slippage < 0 or slippage >= 1:
            issues.append(BacktestIssue("slippageRate", "OUT_OF_RANGE", "must be in [0,1)"))
        for field, value in (
            ("datasetChecksum", self.dataset_checksum),
            ("parameterFingerprint", self.parameter_fingerprint),
            ("contextFingerprint", self.context_fingerprint),
        ):
            if len(value) != 64:
                issues.append(
                    BacktestIssue(field, "SHA256_REQUIRED", "must be a SHA-256 hex digest")
                )
        if self.dataset_schema_version != "1":
            issues.append(
                BacktestIssue("datasetSchemaVersion", "UNSUPPORTED", "only version 1 is supported")
            )
        if not self.contract_version.startswith("1."):
            issues.append(
                BacktestIssue(
                    "contractVersion", "UNSUPPORTED", "only contract major 1 is supported"
                )
            )
        if issues:
            raise BacktestError(
                BacktestErrorCode.CONFIGURATION_INVALID,
                "backtest configuration is invalid",
                tuple(issues),
            )
        object.__setattr__(self, "start_time", start)
        object.__setattr__(self, "end_time", end)
        object.__setattr__(self, "initial_capital", capital)
        object.__setattr__(self, "fee_rate", fee)
        object.__setattr__(self, "slippage_rate", slippage)

    @property
    def execution_config(self) -> dict[str, object]:
        return {
            "feeRate": canonical_decimal(self.fee_rate),
            "initialCapital": canonical_decimal(self.initial_capital),
            "positionModel": "LONG_ONLY",
            "randomSeed": self.random_seed,
            "signalTiming": "NEXT_CANDLE_OPEN",
            "sizing": "ALL_AVAILABLE_CASH",
            "slippageRate": canonical_decimal(self.slippage_rate),
        }

    @property
    def execution_config_fingerprint(self) -> str:
        return canonical_hash(self.execution_config)

    @property
    def input_fingerprint(self) -> str:
        payload: dict[str, object] = {
            "contractVersion": self.contract_version,
            "contextFingerprint": self.context_fingerprint,
            "datasetChecksum": self.dataset_checksum,
            "datasetId": str(self.dataset_id),
            "datasetSchemaVersion": self.dataset_schema_version,
            "endTime": format_utc_millis(self.end_time),
            "executionConfig": self.execution_config,
            "executionPolicyId": str(self.execution_policy_id),
            "executionPolicyVersion": self.execution_policy_version,
            "pair": self.pair,
            "parameterFingerprint": self.parameter_fingerprint,
            "provider": self.provider,
            "startTime": format_utc_millis(self.start_time),
            "strategyDefinitionId": str(self.strategy_definition_id),
            "strategyId": self.strategy_id,
            "strategyVersion": self.strategy_version,
            "timeframe": self.timeframe.value,
        }
        if self.sentiment_provenance:
            payload["sentiment"] = [item.to_payload() for item in self.sentiment_provenance]
        return canonical_hash(payload)


@dataclass(frozen=True, slots=True)
class BacktestRun:
    configuration: BacktestConfiguration
    status: RunStatus
    requested_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        require_utc(self.requested_at)
        if self.started_at is not None:
            require_utc(self.started_at)
        if self.completed_at is not None:
            require_utc(self.completed_at)

    def running(self, now: datetime) -> BacktestRun:
        if self.status is not RunStatus.REQUESTED:
            raise ValueError("only requested runs can start")
        return BacktestRun(self.configuration, RunStatus.RUNNING, self.requested_at, now)

    def completed(self, now: datetime) -> BacktestRun:
        if self.status is not RunStatus.RUNNING:
            raise ValueError("only running runs can complete")
        return BacktestRun(
            self.configuration, RunStatus.COMPLETED, self.requested_at, self.started_at, now
        )

    def failed(self, now: datetime, code: str) -> BacktestRun:
        if self.status is not RunStatus.RUNNING:
            raise ValueError("only running runs can fail")
        return BacktestRun(
            self.configuration,
            RunStatus.FAILED,
            self.requested_at,
            self.started_at,
            now,
            code,
        )
