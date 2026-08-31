from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.errors import install_error_handlers
from crypto_lab.api.middleware import RequestIdMiddleware
from crypto_lab.api.routes import evaluations
from crypto_lab.application.evaluations.compare_results import CompareEvaluationResults
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.evaluation.policy import (
    EvaluationPolicy,
    MetricDirection,
    MetricWeight,
    ScoringPolicy,
)
from crypto_lab.domain.evaluation.result import create_evaluation_result
from crypto_lab.domain.evaluation.scoring import score_metrics
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.persistence import two_trade_result


def _results():
    backtest = two_trade_result()
    evaluation_policy = EvaluationPolicy(UUID(int=601), "standard", "1")
    scoring_policy = ScoringPolicy(
        UUID(int=602),
        "return-only",
        "1",
        "Return only",
        (
            MetricWeight(
                "totalReturn",
                MetricDirection.HIGHER,
                Decimal("-100"),
                Decimal("100"),
                Decimal("1"),
            ),
        ),
        ("evaluationResultId:asc",),
    )
    metrics = calculate_metrics(backtest)
    first = create_evaluation_result(
        backtest,
        evaluation_policy,
        scoring_policy,
        metrics,
        score_metrics(metrics, scoring_policy),
        NOW,
    )
    second = replace(first, id=UUID(int=603), score=first.score + Decimal("1"))
    return first, second


class _Repository:
    def __init__(self, values) -> None:
        self.values = {item.id: item for item in values}

    async def get_many(self, result_ids):
        return tuple(self.values[item] for item in result_ids if item in self.values)

    async def get(self, result_id):
        return self.values.get(result_id)


def _app(values) -> FastAPI:
    app = FastAPI()
    repository = _Repository(values)
    app.state.container = SimpleNamespace(
        compare_evaluations=CompareEvaluationResults(repository),
        evaluation_repository=repository,
    )
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(evaluations.router)
    return app


async def test_comparison_returns_stable_order_without_mutating_results() -> None:
    first, second = _results()
    original = (first.score, second.score, first.content_fingerprint, second.content_fingerprint)
    async with AsyncClient(
        transport=ASGITransport(app=_app((first, second))), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/evaluation-comparisons",
            json={
                "evaluationResultIds": [str(first.id), str(second.id)],
                "mode": "CONTEXTUAL",
            },
        )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["compatible"] is True
    assert data["differences"] == []
    assert [item["id"] for item in data["results"]] == [str(second.id), str(first.id)]
    assert (
        first.score,
        second.score,
        first.content_fingerprint,
        second.content_fingerprint,
    ) == original


async def test_contextual_comparison_reports_every_difference() -> None:
    first, second = _results()
    incompatible = replace(second, scoring_policy_version="2")
    async with AsyncClient(
        transport=ASGITransport(app=_app((first, incompatible))), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/evaluation-comparisons",
            json={
                "evaluationResultIds": [str(first.id), str(incompatible.id)],
                "mode": "CONTEXTUAL",
            },
        )

    data = response.json()["data"]
    assert data["compatible"] is False
    assert data["differences"] == [
        {"dimension": "scoring_policy_version", "values": ["1", "2"]}
    ]


async def test_strict_comparison_rejection_preserves_every_difference() -> None:
    first, second = _results()
    incompatible = replace(second, scoring_policy_version="2")
    async with AsyncClient(
        transport=ASGITransport(app=_app((first, incompatible))), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/evaluation-comparisons",
            json={
                "evaluationResultIds": [str(first.id), str(incompatible.id)],
                "mode": "STRICT",
            },
        )

    body = response.json()
    assert response.status_code == 422
    assert body["error"]["code"] == "EVALUATION_CONTEXT_INCOMPATIBLE"
    assert body["error"]["details"]["differences"] == [
        {"dimension": "scoring_policy_version", "values": ["1", "2"]}
    ]
    assert body["requestId"]


async def test_comparison_rejects_duplicate_and_oversized_id_sets() -> None:
    first, second = _results()
    app = _app((first, second))
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        duplicate = await client.post(
            "/api/v1/evaluation-comparisons",
            json={"evaluationResultIds": [str(first.id), str(first.id)], "mode": "CONTEXTUAL"},
        )
        oversized = await client.post(
            "/api/v1/evaluation-comparisons",
            json={
                "evaluationResultIds": [str(UUID(int=index)) for index in range(1, 22)],
                "mode": "CONTEXTUAL",
            },
        )

    assert duplicate.status_code == 422
    assert duplicate.json()["error"]["code"] == "EVALUATION_COMPARISON_INVALID"
    assert oversized.status_code == 400
    assert oversized.json()["error"]["code"] == "MARKET_REQUEST_MALFORMED"


async def test_missing_evaluation_uses_versioned_not_found_envelope() -> None:
    first, second = _results()
    async with AsyncClient(
        transport=ASGITransport(app=_app((first, second))), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/v1/evaluation-results/00000000-0000-0000-0000-000000000999"
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EVALUATION_RESULT_NOT_FOUND"
