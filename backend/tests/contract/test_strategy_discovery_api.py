from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.routes import strategies
from crypto_lab.api.schemas.strategy import metadata_to_dto
from crypto_lab.application.strategies.discover_strategies import DiscoverStrategies
from crypto_lab.bootstrap.strategies import build_strategy_registry


def test_builtin_discovery_is_deterministic_and_schema_neutral() -> None:
    entries = build_strategy_registry().discover()
    assert [entry.strategy_id for entry in entries] == [
        "bollinger",
        "ma",
        "rsi",
        "support_resistance",
    ]
    payloads = [metadata_to_dto(entry).model_dump(by_alias=True) for entry in entries]
    assert payloads[0]["parameters"][0]["defaultValue"] == 20
    assert payloads[3]["parameters"][0]["defaultValue"] == 120
    assert all(payload["origin"] == "BUILT_IN" for payload in payloads)


async def test_strategy_catalog_endpoint_exposes_all_four_builtins() -> None:
    registry = build_strategy_registry()
    app = FastAPI()
    app.include_router(strategies.router)
    app.state.container = SimpleNamespace(
        strategy_discovery=DiscoverStrategies(registry),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/api/v1/strategies")

    assert response.status_code == 200
    catalog = response.json()["data"]["strategies"]
    assert [item["strategyId"] for item in catalog] == [
        "bollinger",
        "ma",
        "rsi",
        "support_resistance",
    ]
