"""The implementation must stay in sync with the published TV5 contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from crypto_lab.api.schemas.leaderboards import (
    LeaderboardEntryDto,
    LeaderboardSnapshotDto,
    LeaderboardUpdatedEventDto,
    MetricSetDto,
    RankedResultDetailDto,
    TradeDto,
    VisualizationDataDto,
)
from crypto_lab.api.websocket.leaderboard_channel import MAX_SUBSCRIPTIONS_PER_CONNECTION
from crypto_lab.application.leaderboard import errors as error_codes
from crypto_lab.application.leaderboard.get_ranked_result import (
    MAX_VISUALIZATION_INTERVALS,
    TRADE_SORT_FIELDS,
)
from crypto_lab.application.leaderboard.ports import (
    AvailabilityState,
    MarkerShape,
    MarkerTone,
    MarkerType,
    OverlayKind,
)
from crypto_lab.application.leaderboard.query_leaderboard import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)
from crypto_lab.domain.leaderboard.policy import (
    DEFAULT_K,
    MAX_K,
    MIN_K,
    MetricName,
    MetricUnit,
    RankMetric,
    SortDirection,
)

CONTRACTS = Path(__file__).parents[3] / "specs" / "005-leaderboard-visualization" / "contracts"
OPENAPI = CONTRACTS / "openapi.yaml"
EVENTS = CONTRACTS / "leaderboard-events.md"
OVERLAYS = CONTRACTS / "chart-overlays.md"


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))


def schema(document: dict[str, Any], name: str) -> dict[str, Any]:
    return document["components"]["schemas"][name]


def field_names(model: type) -> set[str]:
    return {
        field.alias or name for name, field in model.model_fields.items()  # type: ignore[attr-defined]
    }


def test_rank_metric_and_sort_enums_match(document: dict[str, Any]) -> None:
    assert set(schema(document, "RankMetric")["enum"]) == {item.value for item in RankMetric}
    assert set(schema(document, "MetricName")["enum"]) == {item.value for item in MetricName}
    assert set(schema(document, "SortDirection")["enum"]) == {item.value for item in SortDirection}
    assert set(schema(document, "LeaderboardSortField")["enum"]) == {"RANK"} | {
        item.value for item in RankMetric
    }


def test_metric_units_and_availability_states_match(document: dict[str, Any]) -> None:
    units = schema(document, "MetricDescriptor")["properties"]["unit"]["enum"]
    assert set(units) == {item.value for item in MetricUnit}
    states = schema(document, "Availability")["properties"]["state"]["enum"]
    assert set(states) == {item.value for item in AvailabilityState}


def test_marker_and_overlay_enums_match(document: dict[str, Any]) -> None:
    marker = schema(document, "Marker")["properties"]
    assert set(marker["type"]["enum"]) == {item.value for item in MarkerType}
    assert set(marker["shape"]["enum"]) == {item.value for item in MarkerShape}
    assert set(marker["tone"]["enum"]) == {item.value for item in MarkerTone}
    assert set(schema(document, "Overlay")["properties"]["kind"]["enum"]) == {
        item.value for item in OverlayKind
    }


def test_error_codes_match(document: dict[str, Any]) -> None:
    envelope = schema(document, "ErrorEnvelope")["properties"]
    published = set(envelope["error"]["properties"]["code"]["enum"])
    implemented = {
        error_codes.LEADERBOARD_NOT_FOUND,
        error_codes.LEADERBOARD_ENTRY_NOT_FOUND,
        error_codes.LEADERBOARD_QUERY_INVALID,
        error_codes.LEADERBOARD_RANGE_INVALID,
        error_codes.LEADERBOARD_DEPENDENCY_UNAVAILABLE,
    }
    assert published == implemented
    assert set(schema(document, "ErrorEnvelope")["required"]) == {
        "success",
        "message",
        "error",
        "timestamp",
        "requestId",
    }, "the leaderboard error contract must match the repository-wide envelope"


@pytest.mark.parametrize(
    ("model", "schema_name"),
    [
        (LeaderboardEntryDto, "LeaderboardEntry"),
        (MetricSetDto, "MetricSet"),
        (TradeDto, "Trade"),
    ],
)
def test_required_response_fields_are_implemented(
    document: dict[str, Any],
    model: type,
    schema_name: str,
) -> None:
    required = set(schema(document, schema_name)["required"])
    assert required <= field_names(model)


def test_snapshot_and_detail_expose_every_published_field(document: dict[str, Any]) -> None:
    assert set(schema(document, "LeaderboardSnapshot")["required"]) <= field_names(
        LeaderboardSnapshotDto
    )
    assert set(schema(document, "RankedResultDetail")["required"]) <= field_names(
        RankedResultDetailDto
    )
    assert set(schema(document, "VisualizationData")["required"]) <= field_names(
        VisualizationDataDto
    )


def test_query_bounds_match_the_published_parameters(document: dict[str, Any]) -> None:
    parameters = document["components"]["parameters"]
    page_size = parameters["PageSize"]["schema"]
    assert page_size["maximum"] == MAX_PAGE_SIZE
    assert page_size["default"] == DEFAULT_PAGE_SIZE
    k = document["paths"]["/leaderboards"]["get"]["parameters"][6]["schema"]
    assert (k["minimum"], k["maximum"], k["default"]) == (MIN_K, MAX_K, DEFAULT_K)


def test_trade_sort_fields_match(document: dict[str, Any]) -> None:
    path = "/leaderboards/{leaderboardId}/entries/{evaluationResultId}/trades"
    sort_parameter = next(
        item
        for item in document["paths"][path]["get"]["parameters"]
        if item.get("name") == "sortBy"
    )
    assert set(sort_parameter["schema"]["enum"]) == set(TRADE_SORT_FIELDS)


def test_visualization_range_bound_is_documented(document: dict[str, Any]) -> None:
    path = "/leaderboards/{leaderboardId}/entries/{evaluationResultId}/visualization"
    start = next(
        item
        for item in document["paths"][path]["get"]["parameters"]
        if item.get("name") == "startTime"
    )
    assert str(MAX_VISUALIZATION_INTERVALS) in start["description"]


def test_event_contract_matches_the_published_envelope() -> None:
    text = EVENTS.read_text(encoding="utf-8")
    payload = json.loads(text.split("## Event Envelope v1")[1].split("```json")[1].split("```")[0])
    fields = field_names(LeaderboardUpdatedEventDto)

    assert payload["eventType"] == "LEADERBOARD_UPDATED"
    assert payload["version"] == 1
    assert set(payload) <= fields
    assert "LEADERBOARD_SUBSCRIPTION_LIMITED" in text
    assert MAX_SUBSCRIPTIONS_PER_CONNECTION > 0


def test_subscription_contract_matches_the_implementation() -> None:
    text = EVENTS.read_text(encoding="utf-8")
    message = json.loads(
        text.split("## Subscription Message v1")[1].split("```json")[1].split("```")[0]
    )
    payload = message["payload"]

    assert message["eventType"] == "LEADERBOARD_SUBSCRIBE"
    assert {"scoringPolicyId", "scoringPolicyVersion", "rankBy", "k"} <= set(payload)
    assert RankMetric(payload["rankBy"])


def test_overlay_contract_documents_every_supported_primitive() -> None:
    text = OVERLAYS.read_text(encoding="utf-8")

    for kind in OverlayKind:
        assert f"`{kind.value}`" in text
    for marker in MarkerType:
        assert f"`{marker.value}`" in text
    for shape in MarkerShape:
        assert f"`{shape.value}`" in text
