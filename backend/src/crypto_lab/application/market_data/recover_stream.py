from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from random import random

from crypto_lab.application.market_data.candle_merge import (
    CandleUpdate,
    ClosedCandleConflictError,
    merge_live_candle,
)
from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe, require_utc


class RecoveryState(StrEnum):
    STALE = "STALE"
    RECONNECTING = "RECONNECTING"
    LIVE = "LIVE"
    ERROR = "ERROR"
    PAUSED_OFFLINE = "PAUSED_OFFLINE"


@dataclass(frozen=True, slots=True)
class RecoverySignal:
    state: RecoveryState
    attempt: int = 0
    retry_after_ms: int = 0
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    """Capped exponential backoff with jitter and a bounded automatic attempt window."""

    max_attempts: int = 8
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if not 1 <= self.max_attempts <= 8:
            raise ValueError("max_attempts must be between one and eight")
        if self.initial_delay_seconds <= 0:
            raise ValueError("initial delay must be positive")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max delay must not be below the initial delay")
        if not 0 <= self.jitter_ratio < 1:
            raise ValueError("jitter ratio must be at least zero and less than one")

    def nominal_delay_seconds(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt must be positive")
        return min(self.initial_delay_seconds * (2.0 ** (attempt - 1)), self.max_delay_seconds)

    def jittered_delay_seconds(
        self,
        attempt: int,
        *,
        random_source: Callable[[], float] = random,
    ) -> float:
        nominal = self.nominal_delay_seconds(attempt)
        if self.jitter_ratio == 0:
            return nominal
        ratio = random_source()
        factor = 1.0 + self.jitter_ratio * (2.0 * ratio - 1.0)
        return nominal * factor


class RecoveryController:
    """Owns the bounded recovery cycle state for one market selection."""

    def __init__(
        self,
        policy: RecoveryPolicy | None = None,
        *,
        connectivity: Callable[[], bool] = lambda: True,
    ) -> None:
        self._policy = policy or RecoveryPolicy()
        self._connectivity = connectivity
        self._attempt = 0
        self._disconnected = False

    @property
    def policy(self) -> RecoveryPolicy:
        return self._policy

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def disconnected(self) -> bool:
        return self._disconnected

    @property
    def exhausted(self) -> bool:
        return self._attempt >= self._policy.max_attempts

    def on_disconnect(self, *, reason_code: str | None = None) -> RecoverySignal:
        self._disconnected = True
        return RecoverySignal(
            RecoveryState.STALE,
            attempt=self._attempt,
            reason_code=reason_code or "PROVIDER_DISCONNECTED",
        )

    def begin_reconnect(self) -> RecoverySignal:
        """Start or advance one reconnect attempt; an offline client does not consume budget."""
        if not self._connectivity():
            return RecoverySignal(RecoveryState.PAUSED_OFFLINE, attempt=self._attempt)
        if self.exhausted:
            return RecoverySignal(
                RecoveryState.ERROR,
                attempt=self._attempt,
                reason_code="MARKET_RECOVERY_EXHAUSTED",
            )
        self._attempt += 1
        delay_ms = round(self._policy.jittered_delay_seconds(self._attempt) * 1000)
        return RecoverySignal(
            RecoveryState.RECONNECTING,
            attempt=self._attempt,
            retry_after_ms=delay_ms,
        )

    def on_connected(self) -> RecoverySignal:
        return RecoverySignal(RecoveryState.LIVE, attempt=self._attempt)

    def on_connectivity_restored(self) -> RecoverySignal | None:
        if not self._connectivity():
            return None
        if self._disconnected:
            return self.begin_reconnect()
        return None


def recovery_backfill_range(
    checkpoint: datetime,
    timeframe: Timeframe,
    now: datetime,
) -> TimeRange | None:
    """Aligned closed-interval range after the checkpoint; None when there is no gap."""
    start = checkpoint + timeframe.duration
    end = timeframe.floor(require_utc(now))
    if end <= start:
        return None
    return TimeRange(start, end)


def merge_recovery_batch(
    series: tuple[CandleUpdate, ...],
    candles: Iterable[Candle],
    *,
    limit: int,
) -> tuple[CandleUpdate, ...]:
    """Merge a sorted, deduplicated closed-Candle batch into the live tail.

    Recovery batches are chronological and immutable; conflicting closed identities are
    quarantined rather than raised, and older identities outside the gap are ignored.
    """
    merged = series
    for candle in sorted(candles, key=lambda item: item.open_time):
        try:
            next_series = merge_live_candle(merged, candle, limit=limit)
        except ClosedCandleConflictError:
            continue
        if next_series == merged:
            continue
        merged = next_series
    return merged
