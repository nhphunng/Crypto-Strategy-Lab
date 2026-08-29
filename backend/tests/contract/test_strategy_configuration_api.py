from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.routes import strategies


class _SaveConfiguration:
    def __init__(self) -> None:
        self.received = None

    async def execute(self, command):
        self.received = command
        return {
            "configurationId": "81000000-0000-0000-0000-000000000001",
            "configurationKey": "ma",
            "configurationVersion": 1,
            "displayName": "MA",
            "kind": "SINGLE",
            "rootDefinitionId": "82000000-0000-0000-0000-000000000001",
            "selection": {"provider": "BINANCE", "pair": "SOLUSDT", "timeframe": "1h"},
            "members": [
                {
                    "strategyId": "ma",
                    "strategyVersion": "1.0.0",
                    "definitionId": "83000000-0000-0000-0000-000000000001",
                    "parameters": {"period": 20},
                    "weight": None,
                }
            ],
            "combination": None,
            "contentFingerprint": "a" * 64,
            "createdAt": "2026-08-28T12:00:00.000Z",
        }


async def test_saves_single_strategy_configuration_with_exact_context() -> None:
    saver = _SaveConfiguration()
    app = FastAPI()
    app.include_router(strategies.router)
    app.state.container = SimpleNamespace(save_strategy_configuration=saver)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/strategy-configurations",
            json={
                "displayName": "MA",
                "selection": {
                    "provider": "BINANCE",
                    "pair": "SOLUSDT",
                    "timeframe": "1h",
                },
                "members": [
                    {
                        "strategyId": "ma",
                        "strategyVersion": "1.0.0",
                        "parameters": {"period": 20},
                    }
                ],
                "combination": None,
            },
        )

    assert response.status_code == 201
    payload = response.json()["data"]
    assert UUID(payload["configurationId"])
    assert UUID(payload["rootDefinitionId"])
    assert payload["configurationVersion"] == 1
    assert payload["selection"] == {
        "provider": "BINANCE",
        "pair": "SOLUSDT",
        "timeframe": "1h",
    }
    assert payload["members"] == [
        {
            "strategyId": "ma",
            "strategyVersion": "1.0.0",
            "definitionId": "83000000-0000-0000-0000-000000000001",
            "parameters": {"period": 20},
            "weight": None,
        }
    ]
    assert saver.received is not None


async def test_weighted_composite_requires_exact_weights_summing_to_one() -> None:
    saver = _SaveConfiguration()
    app = FastAPI()
    app.include_router(strategies.router)
    app.state.container = SimpleNamespace(save_strategy_configuration=saver)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/strategy-configurations",
            json={
                "displayName": "MA + RSI · Weighted",
                "selection": {
                    "provider": "BINANCE",
                    "pair": "ETHUSDT",
                    "timeframe": "15m",
                },
                "members": [
                    {
                        "strategyId": "ma",
                        "strategyVersion": "1.0.0",
                        "parameters": {"period": 20},
                    },
                    {
                        "strategyId": "rsi",
                        "strategyVersion": "1.0.0",
                        "parameters": {"period": 14},
                    },
                ],
                "combination": {
                    "method": "WEIGHTED",
                    "tieAction": "HOLD",
                    "buyThreshold": "0.3",
                    "sellThreshold": "-0.3",
                },
            },
        )

    assert response.status_code == 422
    assert saver.received is None
