from __future__ import annotations

from pathlib import Path

import yaml

from crypto_lab.main import create_app


def test_feature_004_openapi_operations_and_analysis_disclaimer_are_registered() -> None:
    document = create_app().openapi()
    paths = document["paths"]
    expected = {
        "/api/v1/backtest-runs",
        "/api/v1/backtest-runs/{run_id}/start",
        "/api/v1/backtest-runs/{run_id}",
        "/api/v1/backtest-results/{result_id}",
        "/api/v1/backtest-results/{result_id}/trades",
        "/api/v1/backtest-results/{result_id}/equity-curve",
        "/api/v1/evaluation-results",
        "/api/v1/evaluation-results/{evaluation_result_id}",
        "/api/v1/evaluation-comparisons",
    }
    assert expected <= paths.keys()
    schemas = document["components"]["schemas"]
    assert "analysisType" in schemas["BacktestResultDto"]["properties"]
    assert "disclaimer" in schemas["EvaluationResultDto"]["properties"]
    assert schemas["ComparisonRequest"]["properties"]["evaluationResultIds"]["maxItems"] == 20
    trade_page = schemas["crypto_lab__api__schemas__backtest_evaluation__TradePageDto"]
    assert {"items", "pagination", "nextCursor"} <= set(trade_page["required"])


def test_feature_004_checked_in_openapi_is_valid_and_matches_public_bounds() -> None:
    contract = Path(__file__).parents[3] / "specs/004-backtest-evaluation/contracts/openapi.yaml"
    document = yaml.safe_load(contract.read_text(encoding="utf-8"))

    assert document["openapi"] == "3.1.0"
    schemas = document["components"]["schemas"]
    assert schemas["ComparisonRequest"]["properties"]["evaluationResultIds"]["maxItems"] == 20
    assert set(schemas["TradePage"]["required"]) == {"items", "pagination", "nextCursor"}
    assert set(schemas["EquityPage"]["required"]) == {"items", "pagination", "nextCursor"}
    assert "error" in schemas["ErrorEnvelope"]["required"]
    assert "data" not in schemas["ErrorEnvelope"]["properties"]
