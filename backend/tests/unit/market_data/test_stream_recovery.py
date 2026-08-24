from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from tests.fixtures.market_data import make_candle

from crypto_lab.application.market_data.candle_merge import CandleUpdate
from crypto_lab.application.market_data.recover_stream import (
    RecoveryController,
    RecoveryPolicy,
    RecoverySignal,
    RecoveryState,
    merge_recovery_batch,
    recovery_backfill_range,
)
from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.domain.market_data.timeframe import Timeframe

SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
OPEN = datetime(2026, 8, 13, 10, 0, tzinfo=UTC)


def test_nominal_delay_doubles_then_caps_at_max_delay() -> None:
    policy = RecoveryPolicy()

    assert [policy.nominal_delay_seconds(attempt) for attempt in range(1, 9)] == [
        1.0,
        2.0,
        4.0,
        8.0,
        16.0,
        30.0,
        30.0,
        30.0,
    ]


def test_jittered_delay_stays_within_ratio_bounds() -> None:
    policy = RecoveryPolicy(jitter_ratio=0.2)
    for attempt in range(1, 9):
        nominal = policy.nominal_delay_seconds(attempt)
        lower = policy.jittered_delay_seconds(attempt, random_source=lambda: 0.0)
        upper = policy.jittered_delay_seconds(attempt, random_source=lambda: 1.0)
        assert lower == pytest.approx(nominal * 0.8)
        assert upper == pytest.approx(nominal * 1.2)
        for _ in range(32):
            jittered = policy.jittered_delay_seconds(attempt, random_source=lambda: 0.37)
            assert nominal * 0.8 <= jittered <= nominal * 1.2


def test_zero_jitter_ratio_is_deterministic() -> None:
    policy = RecoveryPolicy(jitter_ratio=0)

    for attempt in range(1, 9):
        jittered = policy.jittered_delay_seconds(attempt, random_source=lambda: 0.99)
        assert jittered == policy.nominal_delay_seconds(attempt)


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"max_attempts": 0}, "max_attempts"),
        ({"max_attempts": 9}, "max_attempts"),
        ({"initial_delay_seconds": 0}, "initial delay"),
        ({"initial_delay_seconds": -1}, "initial delay"),
        ({"max_delay_seconds": 0.5}, "max delay"),
        ({"jitter_ratio": -0.1}, "jitter"),
        ({"jitter_ratio": 1.0}, "jitter"),
    ],
)
def test_policy_rejects_invalid_configuration(
    overrides: dict[str, object],
    error: str,
) -> None:
    with pytest.raises(ValueError) as caught:
        RecoveryPolicy(**overrides)
    assert error in str(caught.value)


def test_nominal_delay_rejects_non_positive_attempt() -> None:
    with pytest.raises(ValueError):
        RecoveryPolicy().nominal_delay_seconds(0)


def test_disconnect_emits_stale_and_marks_disconnected() -> None:
    controller = RecoveryController()

    signal = controller.on_disconnect(reason_code="PROVIDER_HEARTBEAT_TIMEOUT")

    assert signal == RecoverySignal(
        RecoveryState.STALE,
        attempt=0,
        reason_code="PROVIDER_HEARTBEAT_TIMEOUT",
    )
    assert controller.disconnected is True
    assert controller.attempt == 0


def test_reconnect_attempts_increment_up_to_budget_and_then_error() -> None:
    controller = RecoveryController(RecoveryPolicy(max_attempts=3, jitter_ratio=0))

    first = controller.begin_reconnect()
    second = controller.begin_reconnect()
    third = controller.begin_reconnect()
    exhausted = controller.begin_reconnect()

    assert (first.state, first.attempt, first.retry_after_ms) == (
        RecoveryState.RECONNECTING,
        1,
        1_000,
    )
    assert (second.state, second.attempt, second.retry_after_ms) == (
        RecoveryState.RECONNECTING,
        2,
        2_000,
    )
    assert (third.state, third.attempt, third.retry_after_ms) == (
        RecoveryState.RECONNECTING,
        3,
        4_000,
    )
    assert exhausted == RecoverySignal(
        RecoveryState.ERROR,
        attempt=3,
        reason_code="MARKET_RECOVERY_EXHAUSTED",
    )
    assert controller.exhausted is True
    assert controller.attempt == 3


def test_offline_pause_does_not_consume_the_attempt_budget() -> None:
    online = False
    controller = RecoveryController(connectivity=lambda: online)
    controller.on_disconnect()

    paused = controller.begin_reconnect()
    paused_again = controller.begin_reconnect()

    assert paused.state is RecoveryState.PAUSED_OFFLINE
    assert paused_again.state is RecoveryState.PAUSED_OFFLINE
    assert controller.attempt == 0

    online = True
    resumed = controller.on_connectivity_restored()

    assert resumed is not None
    assert resumed.state is RecoveryState.RECONNECTING
    assert resumed.attempt == 1
    assert resumed.retry_after_ms > 0


def test_connectivity_restored_returns_none_while_still_offline() -> None:
    controller = RecoveryController(connectivity=lambda: False)

    assert controller.on_connectivity_restored() is None
    assert controller.attempt == 0


def test_connected_after_recovery_emits_live() -> None:
    controller = RecoveryController(RecoveryPolicy(max_attempts=2))
    controller.begin_reconnect()

    signal = controller.on_connected()

    assert signal.state is RecoveryState.LIVE
    assert signal.attempt == 1


def test_recovery_backfill_range_covers_closed_intervals_after_checkpoint() -> None:
    checkpoint = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    now = datetime(2026, 8, 13, 10, 30, tzinfo=UTC)

    backfill = recovery_backfill_range(checkpoint, Timeframe.FIVE_MINUTES, now)

    assert backfill is not None
    assert backfill.start_time == datetime(2026, 8, 13, 10, 15, tzinfo=UTC)
    assert backfill.end_time == datetime(2026, 8, 13, 10, 30, tzinfo=UTC)
    assert backfill.expected_opens(Timeframe.FIVE_MINUTES) == (
        datetime(2026, 8, 13, 10, 15, tzinfo=UTC),
        datetime(2026, 8, 13, 10, 20, tzinfo=UTC),
        datetime(2026, 8, 13, 10, 25, tzinfo=UTC),
    )


def test_recovery_backfill_range_is_empty_until_the_next_interval_ends() -> None:
    checkpoint = datetime(2026, 8, 13, 10, 10, tzinfo=UTC)
    now = datetime(2026, 8, 13, 10, 15, tzinfo=UTC)

    assert recovery_backfill_range(checkpoint, Timeframe.FIVE_MINUTES, now) is None
    assert recovery_backfill_range(checkpoint, Timeframe.FIVE_MINUTES, checkpoint) is None


def test_merge_recovery_batch_sorts_and_deduplicates_identities() -> None:
    candle_at = lambda minute, close: make_candle(  # noqa: E731
        OPEN + timedelta(minutes=minute), selection=SELECTION, close=close
    )
    batch = (
        candle_at(10, "102"),
        candle_at(0, "100"),
        candle_at(5, "101"),
        candle_at(10, "102"),
    )

    merged = merge_recovery_batch((), batch, limit=10)

    assert [update.candle.open_time for update in merged] == [
        OPEN,
        OPEN + timedelta(minutes=5),
        OPEN + timedelta(minutes=10),
    ]
    assert [update.revision for update in merged] == [1, 1, 1]


def test_merge_recovery_batch_keeps_accepted_closed_candles_unchanged() -> None:
    accepted = make_candle(OPEN, selection=SELECTION, close="101")
    series = (CandleUpdate(accepted, 1),)
    newer = make_candle(
        OPEN + timedelta(minutes=5),
        selection=SELECTION,
        close="102",
    )

    merged = merge_recovery_batch(series, (accepted, newer), limit=10)

    assert len(merged) == 2
    assert merged[0].candle.open_time == OPEN
    assert merged[0].revision == 1
    assert merged[1].candle.open_time == OPEN + timedelta(minutes=5)


def test_merge_recovery_batch_ignores_older_identities_outside_the_gap() -> None:
    series = (CandleUpdate(make_candle(OPEN, selection=SELECTION, close="101"), 1),)
    older = make_candle(
        OPEN - timedelta(minutes=5),
        selection=SELECTION,
        close="100",
    )

    assert merge_recovery_batch(series, (older,), limit=10) == series


def test_merge_recovery_batch_skips_conflicting_closed_candles_without_raising() -> None:
    accepted = make_candle(OPEN, selection=SELECTION, close="101")
    series = (CandleUpdate(accepted, 1),)
    conflicting = make_candle(OPEN, selection=SELECTION, close="101.5")

    assert merge_recovery_batch(series, (conflicting,), limit=10) == series


def test_merge_recovery_batch_respects_the_bounded_limit() -> None:
    candles = tuple(
        make_candle(OPEN + index * timedelta(minutes=5), selection=SELECTION) for index in range(5)
    )

    merged = merge_recovery_batch((), candles, limit=3)

    assert len(merged) == 3
    assert merged[0].candle.open_time == OPEN + 2 * timedelta(minutes=5)
    assert merged[-1].candle.open_time == OPEN + 4 * timedelta(minutes=5)
