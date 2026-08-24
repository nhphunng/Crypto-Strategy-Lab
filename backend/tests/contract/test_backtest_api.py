from __future__ import annotations

import re
from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.errors import install_error_handlers
from crypto_lab.api.middleware import RequestIdMiddleware
from crypto_lab.api.routes import backtests
from crypto_lab.application.backtests.ports import BacktestDataset
from crypto_lab.domain.backtest.configuration import BacktestRun, RunStatus
from crypto_lab.domain.market_data.dataset import CandleDataset, DatasetStatus
from crypto_lab.domain.strategy.signal import SignalAction
from tests.fixtures.backtest_evaluation.cross_feature import NOW, deterministic_inputs
from tests.fixtures.backtest_evaluation.persistence import two_trade_result

INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class _CreateRun:
    def __init__(self) -> None:
        self.run: BacktestRun | None = None

    async def execute(self, configuration):
        self.run = BacktestRun(configuration, RunStatus.REQUESTED, NOW)
        return self.run


class _Repository:
    def __init__(self, creator: _CreateRun) -> None:
        self.creator = creator

    async def get_run(self, run_id):
        run = self.creator.run
        return run if run is not None and run.configuration.run_id == run_id else None


class _Execute:
    async def execute(self, _run_id, _request_id):
        return two_trade_result()


class _ResultReader:
    async def get(self, result_id):
        result = two_trade_result()
        return result if result.id == result_id else None


def _container():
    configuration, candles, analysis, _policy = deterministic_inputs(
        (
            SignalAction.BUY,
            SignalAction.SELL,
            SignalAction.BUY,
            SignalAction.SELL,
            SignalAction.HOLD,
        ),
        ("100", "100", "120", "100", "130"),
    )
    metadata = CandleDataset(
        configuration.dataset_id,
        "1",
        SimpleNamespace(
            provider=configuration.provider,
            pair=configuration.pair,
            timeframe=configuration.timeframe,
        ),
        SimpleNamespace(start_time=configuration.start_time, end_time=configuration.end_time),
        DatasetStatus.COMPLETE,
        len(candles),
        configuration.dataset_checksum,
        None,
        NOW,
        NOW,
        NOW,
    )
    creator = _CreateRun()
    return SimpleNamespace(
        backtest_datasets=SimpleNamespace(
            get_complete=lambda _id: _async_value(BacktestDataset(metadata, candles))
        ),
        backtest_strategy_analyzer=SimpleNamespace(
            analyze=lambda *_args: _async_value(analysis)
        ),
        create_backtest=creator,
        execute_backtest=_Execute(),
        backtest_repository=_Repository(creator),
        get_backtest=_ResultReader(),
    ), configuration


async def _async_value(value):
    return value


def _app(container) -> FastAPI:
    app = FastAPI()
    app.state.container = container
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(backtests.router)
    return app


def _request(configuration) -> dict[str, object]:
    return {
        "jobId": str(configuration.job_id),
        "datasetId": str(configuration.dataset_id),
        "datasetSchemaVersion": configuration.dataset_schema_version,
        "datasetChecksum": configuration.dataset_checksum,
        "strategyDefinitionId": str(configuration.strategy_definition_id),
        "strategyVersion": configuration.strategy_version,
        "contractVersion": configuration.contract_version,
        "executionPolicyId": str(configuration.execution_policy_id),
        "executionPolicyVersion": configuration.execution_policy_version,
        "initialCapital": str(configuration.initial_capital),
        "feeRate": str(configuration.fee_rate),
        "slippageRate": str(configuration.slippage_rate),
        "randomSeed": configuration.random_seed,
    }


async def test_create_start_and_get_follow_the_versioned_lifecycle_contract() -> None:
    container, configuration = _container()
    async with AsyncClient(
        transport=ASGITransport(app=_app(container)), base_url="http://testserver"
    ) as client:
        created = await client.post("/api/v1/backtest-runs", json=_request(configuration))
        run_id = created.json()["data"]["id"]
        started = await client.post(f"/api/v1/backtest-runs/{run_id}/start")
        loaded = await client.get(f"/api/v1/backtest-runs/{run_id}")
        result_id = started.json()["data"]["id"]
        result = await client.get(f"/api/v1/backtest-results/{result_id}")

    for response in (created, started, loaded, result):
        body = response.json()
        assert response.status_code in (200, 201)
        assert body["success"] is True
        assert body["message"]
        assert INSTANT.fullmatch(body["timestamp"])
        assert body["requestId"]
    assert created.json()["data"]["status"] == "REQUESTED"
    assert loaded.json()["data"]["jobId"] == str(configuration.job_id)
    assert started.json()["data"]["analysisType"] == "HISTORICAL_SIMULATION"
    assert "not investment advice" in result.json()["data"]["disclaimer"].lower()


async def test_invalid_configuration_returns_stable_backtest_validation_code() -> None:
    container, configuration = _container()
    payload = _request(configuration)
    payload.update({"initialCapital": "0", "feeRate": "-1"})
    async with AsyncClient(
        transport=ASGITransport(app=_app(container)), base_url="http://testserver"
    ) as client:
        response = await client.post("/api/v1/backtest-runs", json=payload)

    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "BACKTEST_CONFIGURATION_INVALID"
    assert body["error"]["retryable"] is False
    assert set(body["error"]["details"]["fields"]) == {"feeRate", "initialCapital"}
    assert "traceback" not in response.text.lower()


async def test_dataset_identity_conflict_is_categorized_without_partial_success() -> None:
    container, configuration = _container()
    payload = _request(configuration)
    payload["datasetChecksum"] = "f" * 64
    async with AsyncClient(
        transport=ASGITransport(app=_app(container)), base_url="http://testserver"
    ) as client:
        response = await client.post("/api/v1/backtest-runs", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BACKTEST_DATASET_INTEGRITY_FAILED"
    assert "data" not in response.json()


async def test_missing_run_and_result_use_safe_versioned_error_envelopes() -> None:
    container, _configuration = _container()
    missing = "00000000-0000-0000-0000-000000000999"
    async with AsyncClient(
        transport=ASGITransport(app=_app(container)), base_url="http://testserver"
    ) as client:
        run = await client.get(f"/api/v1/backtest-runs/{missing}")
        result = await client.get(f"/api/v1/backtest-results/{missing}")

    assert run.status_code == result.status_code == 404
    assert run.json()["error"]["code"] == "BACKTEST_RUN_NOT_FOUND"
    assert result.json()["error"]["code"] == "BACKTEST_RESULT_NOT_FOUND"
    for response in (run, result):
        assert response.json()["success"] is False
        assert response.json()["requestId"]
        assert "traceback" not in response.text.lower()
