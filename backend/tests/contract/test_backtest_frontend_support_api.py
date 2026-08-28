from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.dependencies import (
    BALANCED_SCORING_POLICY,
    EVALUATION_POLICY,
    EXECUTION_POLICY,
)
from crypto_lab.api.routes import backtests, strategies
from crypto_lab.api.schemas.backtest_evaluation import policy_bundle_to_dto
from crypto_lab.bootstrap.strategies import build_strategy_registry


class _Definitions:
    async def create_or_resolve(self, definition):
        return definition


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 24, 0, 0, tzinfo=UTC)


async def test_frontend_can_resolve_exact_builtin_definition_and_policy_identities() -> None:
    registry = build_strategy_registry()
    app = FastAPI()
    app.include_router(strategies.router)
    app.include_router(backtests.router)
    app.state.container = SimpleNamespace(
        strategy_registry=registry,
        strategy_discovery=SimpleNamespace(
            get=lambda strategy_id, version: registry.metadata(
                strategy_id, registry.discover()[0].strategy_version
            )
        ),
        strategy_definitions=_Definitions(),
        clock=_Clock(),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/strategy-definitions",
            json={"strategyId": "ma", "strategyVersion": "1.0.0", "parameters": {"period": 20}},
        )
        policies = await client.get("/api/v1/backtest-evaluation/policies")

    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["strategyId"] == "ma"
    assert payload["strategyVersion"] == "1.0.0"
    assert payload["parameters"] == {"period": 20}
    assert len(payload["definitionId"]) == 36

    assert policies.status_code == 200
    assert policies.json()["data"] == policy_bundle_to_dto(
        EXECUTION_POLICY, EVALUATION_POLICY, BALANCED_SCORING_POLICY
    ).model_dump(by_alias=True, mode="json")
