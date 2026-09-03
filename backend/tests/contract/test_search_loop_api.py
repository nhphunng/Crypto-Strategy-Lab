from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from crypto_lab.api.routes.search_loop import router
from crypto_lab.application.evaluations.auto_evaluate import SearchLoopRunner
from tests.unit.evaluation.test_search_loop import CountingPipeline, FixedClock


async def test_status_pause_and_resume_use_the_background_runner() -> None:
    runner = SearchLoopRunner(CountingPipeline(), FixedClock())
    app = FastAPI()
    app.state.container = SimpleNamespace(search_loop=runner)
    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        runner.start()
        try:
            assert (await client.get("/api/v1/search-loop/status")).json()["data"][
                "status"
            ] == "RUNNING"
            assert (await client.post("/api/v1/search-loop/pause")).json()["data"][
                "status"
            ] == "PAUSED"
            assert (await client.post("/api/v1/search-loop/resume")).json()["data"][
                "status"
            ] == "RUNNING"
        finally:
            await runner.stop()


async def test_disabled_search_loop_reports_unavailable() -> None:
    app = FastAPI()
    app.state.container = SimpleNamespace(search_loop=None)
    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/search-loop/status")).status_code == 503
