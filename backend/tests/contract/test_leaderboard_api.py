"""REST contract for the Top-K snapshot, query controls, and error envelopes."""

from __future__ import annotations

import re

import pytest
from httpx import AsyncClient

from tests.fixtures.leaderboard import LeaderboardFixture

pytestmark = pytest.mark.integration

DECIMAL = re.compile(r"^-?[0-9]+(\.[0-9]+)?$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def params(fixture: LeaderboardFixture, **overrides: object) -> dict[str, object]:
    query: dict[str, object] = {
        "scoringPolicyId": fixture.scoring_policy_id,
        "scoringPolicyVersion": fixture.scoring_policy_version,
        "rankBy": "OVERALL_SCORE",
        "pair": fixture.pair,
        "timeframe": fixture.timeframe,
        "k": 10,
    }
    query.update(overrides)
    return query


async def snapshot(client: AsyncClient, fixture: LeaderboardFixture, **overrides: object):
    response = await client.get("/api/v1/leaderboards", params=params(fixture, **overrides))
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def test_snapshot_envelope_matches_the_contract(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    response = await leaderboard_client.get(
        "/api/v1/leaderboards", params=params(seeded_leaderboard)
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["message"]
    assert INSTANT.fullmatch(body["timestamp"])
    assert body["requestId"]
    data = body["data"]
    for field in (
        "leaderboardId",
        "scopeKey",
        "scoringPolicyId",
        "scoringPolicyVersion",
        "rankBy",
        "k",
        "projectionVersion",
        "updatedAt",
        "metricMetadata",
        "entries",
        "pagination",
    ):
        assert field in data


async def test_top_k_rows_expose_metrics_and_immutable_provenance(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard)

    assert data["pagination"]["total"] == 10
    assert [row["rank"] for row in data["entries"]] == list(range(1, 11))
    for row in data["entries"]:
        assert DECIMAL.fullmatch(row["score"])
        assert DECIMAL.fullmatch(row["metrics"]["totalReturn"])
        assert DECIMAL.fullmatch(row["metrics"]["winRate"])
        assert DECIMAL.fullmatch(row["metrics"]["maxDrawdown"])
        assert isinstance(row["metrics"]["numberOfTrades"], int)
        assert INSTANT.fullmatch(row["startTime"])
        assert INSTANT.fullmatch(row["updatedAt"])
        assert row["strategy"]["strategyVersion"] == "3"
        assert row["scoringPolicyVersion"] == seeded_leaderboard.scoring_policy_version
        assert row["projectionVersion"] >= 1


async def test_metric_metadata_documents_direction_and_unit(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard)
    metadata = {item["metric"]: item for item in data["metricMetadata"]}

    assert metadata["MAX_DRAWDOWN"]["direction"] == "ASC"
    assert metadata["TOTAL_RETURN"]["direction"] == "DESC"
    assert metadata["NUMBER_OF_TRADES"]["unit"] == "COUNT"
    assert metadata["OVERALL_SCORE"]["unit"] == "SCORE"


async def test_snapshot_carries_the_simulated_analysis_disclaimer(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard)

    assert "not investment advice" in data["disclaimer"].lower()
    assert "guarantee" not in data["disclaimer"].lower().replace("does not guarantee", "")


async def test_repeated_requests_return_the_same_deterministic_order(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    first = await snapshot(leaderboard_client, seeded_leaderboard)
    second = await snapshot(leaderboard_client, seeded_leaderboard)

    assert [row["evaluationResultId"] for row in first["entries"]] == [
        row["evaluationResultId"] for row in second["entries"]
    ]
    assert first["projectionVersion"] == second["projectionVersion"]
    tie_first, tie_second = (str(item) for item in seeded_leaderboard.tie_evaluation_ids)
    order = [row["evaluationResultId"] for row in first["entries"]]
    assert order.index(tie_first) < order.index(tie_second)


async def test_presentation_sort_does_not_change_membership_or_rank(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    default = await snapshot(leaderboard_client, seeded_leaderboard)
    sorted_by_drawdown = await snapshot(
        leaderboard_client, seeded_leaderboard, sortBy="MAX_DRAWDOWN"
    )

    assert {row["evaluationResultId"] for row in default["entries"]} == {
        row["evaluationResultId"] for row in sorted_by_drawdown["entries"]
    }
    drawdowns = [float(row["metrics"]["maxDrawdown"]) for row in sorted_by_drawdown["entries"]]
    assert drawdowns == sorted(drawdowns)
    by_id = {row["evaluationResultId"]: row["rank"] for row in default["entries"]}
    for row in sorted_by_drawdown["entries"]:
        assert row["rank"] == by_id[row["evaluationResultId"]]


async def test_metric_filters_reduce_the_view_without_changing_ranks(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard, minScore="80")

    assert [row["rank"] for row in data["entries"]] == [1, 2, 3, 4, 5]
    assert data["pagination"]["total"] == 5
    assert data["k"] == 10


async def test_sharpe_filter_excludes_rows_without_the_metric(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard, minSharpeRatio="0.5")

    assert all(row["metrics"]["sharpeRatio"] is not None for row in data["entries"])


async def test_pagination_bounds_the_returned_view(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    page_two = await snapshot(leaderboard_client, seeded_leaderboard, page=2, pageSize=4)

    assert page_two["pagination"] == {"page": 2, "pageSize": 4, "total": 10}
    assert [row["rank"] for row in page_two["entries"]] == [5, 6, 7, 8]


async def test_page_beyond_the_result_set_returns_an_empty_page(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard, page=9, pageSize=25)

    assert data["entries"] == []
    assert data["pagination"] == {"page": 9, "pageSize": 25, "total": 10}


async def test_a_different_k_resolves_a_separate_projection(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    ten = await snapshot(leaderboard_client, seeded_leaderboard, k=10)
    three = await snapshot(leaderboard_client, seeded_leaderboard, k=3)

    assert ten["leaderboardId"] != three["leaderboardId"]
    assert len(three["entries"]) == 3


async def test_ranking_by_another_metric_resolves_a_separate_projection(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    by_drawdown = await snapshot(leaderboard_client, seeded_leaderboard, rankBy="MAX_DRAWDOWN")

    drawdowns = [float(row["metrics"]["maxDrawdown"]) for row in by_drawdown["entries"]]
    assert drawdowns == sorted(drawdowns)
    assert by_drawdown["rankBy"] == "MAX_DRAWDOWN"


async def test_no_trade_entry_remains_visible_with_explicit_zero_metrics(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    data = await snapshot(leaderboard_client, seeded_leaderboard)
    row = next(
        item
        for item in data["entries"]
        if item["evaluationResultId"] == str(seeded_leaderboard.no_trade_evaluation_id)
    )

    assert row["metrics"]["numberOfTrades"] == 0
    assert row["metrics"]["sharpeRatio"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"k": 0},
        {"k": 201},
        {"rankBy": "PROFIT"},
        {"sortBy": "NUMBER_OF_TRADES"},
        {"sortDirection": "SIDEWAYS"},
        {"minScore": "abc"},
        {"page": 0},
        {"pageSize": 500},
        {"pair": "btc"},
        {"timeframe": "3m"},
    ],
)
async def test_invalid_query_returns_the_standard_validation_error(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
    overrides: dict[str, object],
) -> None:
    response = await leaderboard_client.get(
        "/api/v1/leaderboards", params=params(seeded_leaderboard, **overrides)
    )
    body = response.json()

    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "LEADERBOARD_QUERY_INVALID"
    assert body["error"]["retryable"] is False
    assert body["requestId"]


async def test_unpublished_scoring_policy_is_reported_as_missing_not_malformed(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    """A deployment whose Evaluation feature published nothing answers this way."""

    response = await leaderboard_client.get(
        "/api/v1/leaderboards",
        params=params(seeded_leaderboard, scoringPolicyId="not-published"),
    )
    body = response.json()

    assert response.status_code == 404
    assert body["error"]["code"] == "LEADERBOARD_POLICY_NOT_PUBLISHED"
    assert body["error"]["details"]["scoringPolicyId"] == "not-published"


async def test_policies_endpoint_lists_the_selectable_ranking_definitions(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    response = await leaderboard_client.get("/api/v1/leaderboards/policies")
    data = response.json()["data"]

    assert response.status_code == 200
    policy = next(
        item
        for item in data["policies"]
        if item["scoringPolicyVersion"] == seeded_leaderboard.scoring_policy_version
    )
    assert policy["scoringPolicyId"] == seeded_leaderboard.scoring_policy_id
    assert policy["defaultRankMetric"] == "OVERALL_SCORE"
    assert policy["name"]
    assert policy["evaluationCount"] == len(seeded_leaderboard.candidates)


async def test_policies_endpoint_reports_a_published_policy_with_no_candidate_yet(
    leaderboard_client: AsyncClient,
) -> None:
    """The clean-deployment case: a real policy, zero evaluations, and no error.

    The platform publishes its own scoring policy at startup, whose version is
    not the demo fixture's. A client that hardcoded the fixture identity is
    exactly how the deployed leaderboard used to fail.
    """

    response = await leaderboard_client.get("/api/v1/leaderboards/policies")
    policies = response.json()["data"]["policies"]

    assert response.status_code == 200
    assert policies, "the platform publishes at least one ranking definition"
    assert all(item["evaluationCount"] == 0 for item in policies)
    assert all(item["scoringPolicyVersion"] != "2" for item in policies)


async def test_missing_required_projection_identity_is_rejected(
    leaderboard_client: AsyncClient,
    seeded_leaderboard: LeaderboardFixture,
) -> None:
    response = await leaderboard_client.get(
        "/api/v1/leaderboards",
        params={"scoringPolicyId": seeded_leaderboard.scoring_policy_id},
    )

    assert response.status_code in (400, 422)
    assert response.json()["success"] is False
