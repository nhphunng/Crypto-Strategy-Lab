from __future__ import annotations

import re
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.errors import install_error_handlers
from crypto_lab.api.middleware import RequestIdMiddleware
from crypto_lab.api.routes import backtests
from tests.fixtures.backtest_evaluation.persistence import two_trade_result

DECIMAL = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class _Reader:
    def __init__(self) -> None:
        self.result = two_trade_result()

    async def counts(self, result_id):
        if result_id != self.result.id:
            return None
        return len(self.result.trades), len(self.result.equity_curve.points)

    async def trades(self, result_id, cursor, limit):
        assert result_id == self.result.id
        return _page(self.result.trades, cursor, limit)

    async def equity(self, result_id, cursor, limit):
        assert result_id == self.result.id
        return _page(self.result.equity_curve.points, cursor, limit)


def _page(items, cursor, limit):
    offset = int(cursor or "0")
    page = tuple(items[offset : offset + limit])
    next_cursor = str(offset + limit) if offset + limit < len(items) else None
    return page, next_cursor


def _app(reader: _Reader) -> FastAPI:
    app = FastAPI()
    app.state.container = SimpleNamespace(get_backtest=reader)
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(backtests.router)
    return app


async def test_trade_pages_are_bounded_ordered_and_contract_encoded() -> None:
    reader = _Reader()
    async with AsyncClient(
        transport=ASGITransport(app=_app(reader)), base_url="http://testserver"
    ) as client:
        first = await client.get(
            f"/api/v1/backtest-results/{reader.result.id}/trades",
            params={"page": 1, "pageSize": 1},
        )
        second = await client.get(
            f"/api/v1/backtest-results/{reader.result.id}/trades",
            params={"page": 2, "pageSize": 1},
        )

    first_data, second_data = first.json()["data"], second.json()["data"]
    assert first_data["pagination"] == {"page": 1, "pageSize": 1, "total": 2}
    assert second_data["pagination"] == {"page": 2, "pageSize": 1, "total": 2}
    assert first_data["nextCursor"] == "1"
    assert second_data["nextCursor"] is None
    rows = first_data["items"] + second_data["items"]
    assert [row["sequence"] for row in rows] == [0, 1]
    for row in rows:
        assert row["entrySignalId"]
        assert row["side"] == "LONG"
        assert row["closeReason"] in {"SELL_SIGNAL", "END_OF_RANGE"}
        assert INSTANT.fullmatch(row["entryTime"])
        assert INSTANT.fullmatch(row["exitTime"])
        for field in (
            "entryReferencePrice",
            "exitReferencePrice",
            "entryPrice",
            "exitPrice",
            "quantity",
            "entryFee",
            "exitFee",
            "profitLoss",
            "returnPercent",
        ):
            assert DECIMAL.fullmatch(row[field])


async def test_equity_pages_preserve_exact_count_order_and_utc_values() -> None:
    reader = _Reader()
    async with AsyncClient(
        transport=ASGITransport(app=_app(reader)), base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/api/v1/backtest-results/{reader.result.id}/equity-curve",
            params={"page": 2, "pageSize": 2},
        )

    data = response.json()["data"]
    assert data["pagination"] == {"page": 2, "pageSize": 2, "total": 5}
    assert [row["position"] for row in data["items"]] == [2, 3]
    assert data["nextCursor"] == "4"
    for row in data["items"]:
        assert INSTANT.fullmatch(row["candleOpenTime"])
        assert INSTANT.fullmatch(row["valuedAt"])
        assert DECIMAL.fullmatch(row["equity"])


async def test_detail_page_size_is_capped_at_two_hundred() -> None:
    reader = _Reader()
    async with AsyncClient(
        transport=ASGITransport(app=_app(reader)), base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/api/v1/backtest-results/{reader.result.id}/trades",
            params={"pageSize": 201},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MARKET_REQUEST_MALFORMED"
