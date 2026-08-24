"""Pure ranking rules: eligibility, direction, ties, K bounds, and identity."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from crypto_lab.domain.leaderboard.entry import (
    LeaderboardEntry,
    MetricSet,
    RankableCandidate,
    StrategySummary,
    assert_projection_invariants,
)
from crypto_lab.domain.leaderboard.policy import (
    ExclusionReason,
    LeaderboardIdentity,
    LeaderboardScope,
    ProjectionVersion,
    RankMetric,
    ScoringPolicy,
    ScoringPolicyRef,
)
from crypto_lab.domain.leaderboard.ranking import diff_projection, rank_candidates
from crypto_lab.domain.market_data.timeframe import Timeframe

POLICY_REF = ScoringPolicyRef("balanced", "2")
EVALUATED_AT = datetime(2026, 7, 3, 12, 0, tzinfo=UTC)


def policy(**overrides: object) -> ScoringPolicy:
    return ScoringPolicy.from_rules(
        POLICY_REF,
        name="Balanced v2",
        default_rank_metric="OVERALL_SCORE",
        rules=dict(overrides) or None,
    )


def candidate(
    index: int,
    *,
    score: str = "50",
    total_return: str = "10",
    win_rate: str = "50",
    max_drawdown: str = "20",
    trades: int = 3,
    sharpe: str | None = "1.0",
    eligible: bool = True,
    policy_ref: ScoringPolicyRef = POLICY_REF,
    evaluated_offset: int = 0,
) -> RankableCandidate:
    identifier = UUID(int=index)
    return RankableCandidate(
        evaluation_result_id=identifier,
        run_id=UUID(int=1000 + index),
        job_id=UUID(int=2000 + index),
        backtest_result_id=UUID(int=3000 + index),
        dataset_id=UUID(int=4000),
        pair="BTCUSDT",
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=datetime(2026, 7, 1, tzinfo=UTC),
        end_time=datetime(2026, 7, 3, tzinfo=UTC),
        strategy=StrategySummary(f"strategy-{index}", "3", f"Strategy {index}"),
        metrics=MetricSet(
            total_return=Decimal(total_return),
            win_rate=Decimal(win_rate),
            max_drawdown=Decimal(max_drawdown),
            number_of_trades=trades,
            sharpe_ratio=None if sharpe is None else Decimal(sharpe),
            score=Decimal(score),
        ),
        policy=policy_ref,
        evaluated_at=EVALUATED_AT + timedelta(seconds=evaluated_offset),
        upstream_eligible=eligible,
    )


def rank(candidates, *, metric=RankMetric.OVERALL_SCORE, k=10, scoring=None, version=1):
    return rank_candidates(
        candidates,
        policy=scoring or policy(),
        rank_metric=metric,
        k=k,
        projection_version=ProjectionVersion(version),
    )


def test_orders_by_score_descending_and_assigns_contiguous_ranks() -> None:
    outcome = rank([candidate(1, score="70"), candidate(2, score="90"), candidate(3, score="80")])

    assert outcome.ranked_ids == (UUID(int=2), UUID(int=3), UUID(int=1))
    assert [entry.rank for entry in outcome.entries] == [1, 2, 3]


def test_max_drawdown_ranks_the_smaller_magnitude_first() -> None:
    outcome = rank(
        [candidate(1, max_drawdown="25"), candidate(2, max_drawdown="10")],
        metric=RankMetric.MAX_DRAWDOWN,
    )

    assert outcome.ranked_ids == (UUID(int=2), UUID(int=1))


def test_tie_is_resolved_deterministically_by_the_policy_key() -> None:
    tied = [
        candidate(2, score="80", total_return="24"),
        candidate(1, score="80", total_return="26"),
    ]

    first = rank(tied)
    second = rank(list(reversed(tied)))

    assert first.ranked_ids == (UUID(int=1), UUID(int=2))
    assert second.ranked_ids == first.ranked_ids


def test_identical_metrics_fall_back_to_the_immutable_evaluation_identity() -> None:
    outcome = rank([candidate(9), candidate(4)])

    assert outcome.ranked_ids == (UUID(int=4), UUID(int=9))


def test_fewer_than_k_returns_every_qualifying_candidate() -> None:
    outcome = rank([candidate(1), candidate(2)], k=10)

    assert len(outcome.entries) == 2


def test_k_bounds_the_projection_and_displaces_the_weakest_candidate() -> None:
    outcome = rank(
        [candidate(index, score=str(50 + index)) for index in range(1, 6)],
        k=3,
    )

    assert outcome.ranked_ids == (UUID(int=5), UUID(int=4), UUID(int=3))


def test_upstream_ineligible_candidate_is_excluded_with_a_visible_reason() -> None:
    outcome = rank([candidate(1, score="99", eligible=False), candidate(2, score="10")])

    assert outcome.ranked_ids == (UUID(int=2),)
    assert outcome.excluded[0].reason is ExclusionReason.UPSTREAM_INELIGIBLE


def test_missing_rank_metric_is_excluded_rather_than_treated_as_superior() -> None:
    outcome = rank(
        [candidate(1, sharpe=None), candidate(2, sharpe="0.1")],
        metric=RankMetric.SHARPE_RATIO,
    )

    assert outcome.ranked_ids == (UUID(int=2),)
    assert outcome.excluded[0].reason is ExclusionReason.METRIC_UNAVAILABLE


def test_missing_tie_breaker_metric_never_outranks_a_present_one() -> None:
    outcome = rank(
        [candidate(1, score="80", sharpe=None), candidate(2, score="80")],
        scoring=policy(tieBreakers=["OVERALL_SCORE", "SHARPE_RATIO"]),
    )

    assert outcome.ranked_ids == (UUID(int=2), UUID(int=1))


def test_no_trade_result_ranks_when_the_policy_allows_it() -> None:
    outcome = rank([candidate(1, trades=0, score="60"), candidate(2, score="50")])

    assert outcome.ranked_ids == (UUID(int=1), UUID(int=2))


def test_no_trade_result_is_excluded_when_the_policy_forbids_it() -> None:
    outcome = rank(
        [candidate(1, trades=0, score="60"), candidate(2, score="50")],
        scoring=policy(eligibilityRules={"excludeNoTrade": True}),
    )

    assert outcome.ranked_ids == (UUID(int=2),)
    assert outcome.excluded[0].reason is ExclusionReason.NO_TRADES


def test_candidate_from_another_policy_version_never_enters_the_projection() -> None:
    outcome = rank([candidate(1, policy_ref=ScoringPolicyRef("balanced", "1"))])

    assert outcome.entries == ()
    assert outcome.excluded[0].reason is ExclusionReason.POLICY_VERSION_MISMATCH


def test_non_finite_metric_is_rejected_before_ranking() -> None:
    with pytest.raises(ValueError):
        MetricSet(
            total_return=Decimal("NaN"),
            win_rate=Decimal("50"),
            max_drawdown=Decimal("10"),
            number_of_trades=1,
        )


def test_repeated_ranking_of_the_same_inputs_is_stable() -> None:
    candidates = [candidate(index, score=str(60 + index % 3)) for index in range(1, 12)]

    assert rank(candidates).ranked_ids == rank(list(reversed(candidates))).ranked_ids


def test_different_k_or_metric_is_a_different_projection_identity() -> None:
    scope = LeaderboardScope(pair="BTCUSDT", timeframe=Timeframe.FIFTEEN_MINUTES)
    base = LeaderboardIdentity(scope, POLICY_REF, RankMetric.OVERALL_SCORE, 10)

    assert base != LeaderboardIdentity(scope, POLICY_REF, RankMetric.OVERALL_SCORE, 5)
    assert base != LeaderboardIdentity(scope, POLICY_REF, RankMetric.TOTAL_RETURN, 10)
    assert base.scope_key == "pair:BTCUSDT|timeframe:15m|run:*"


def test_k_outside_the_documented_bounds_is_rejected() -> None:
    scope = LeaderboardScope()
    with pytest.raises(ValueError):
        LeaderboardIdentity(scope, POLICY_REF, RankMetric.OVERALL_SCORE, 0)
    with pytest.raises(ValueError):
        LeaderboardIdentity(scope, POLICY_REF, RankMetric.OVERALL_SCORE, 201)


def test_diff_reports_added_removed_and_moved_identities() -> None:
    before = rank([candidate(1, score="90"), candidate(2, score="80")]).entries
    after = rank(
        [candidate(1, score="90"), candidate(3, score="85"), candidate(2, score="80")]
    ).entries

    change = diff_projection(before, after)

    assert change.added == (UUID(int=3),)
    assert change.moved == (UUID(int=2),)
    assert change.removed == ()
    assert change.changed is True


def test_identical_ordering_reports_no_visible_change() -> None:
    entries = rank([candidate(1, score="90"), candidate(2, score="80")]).entries

    assert diff_projection(entries, entries).changed is False


def test_projection_invariants_reject_gaps_and_duplicates() -> None:
    version = ProjectionVersion(1)
    with pytest.raises(ValueError):
        assert_projection_invariants(
            (
                LeaderboardEntry(UUID(int=1), 1, version, ()),
                LeaderboardEntry(UUID(int=2), 3, version, ()),
            ),
            k=10,
        )
    with pytest.raises(ValueError):
        assert_projection_invariants(
            (
                LeaderboardEntry(UUID(int=1), 1, version, ()),
                LeaderboardEntry(UUID(int=1), 2, version, ()),
            ),
            k=10,
        )


def test_sort_key_records_the_exact_comparison_components() -> None:
    outcome = rank([candidate(1, score="82.10")])

    assert outcome.entries[0].sort_key[0] == "OVERALL_SCORE:DESC:82.1"
    assert outcome.entries[0].sort_key[-1].startswith("EVALUATION_RESULT_ID:ASC:")
