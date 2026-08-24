from __future__ import annotations

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
