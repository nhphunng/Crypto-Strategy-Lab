from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from crypto_lab.api.dependencies import Container, build_container
from crypto_lab.api.errors import install_error_handlers
from crypto_lab.api.middleware import RequestIdMiddleware
from crypto_lab.api.routes.market_data import router as market_data_router
from crypto_lab.api.routes.strategies import router as strategies_router
from crypto_lab.api.routes.strategy_generation import router as strategy_generation_router
from crypto_lab.api.websocket.market_data_channel import router as market_data_websocket_router
from crypto_lab.infrastructure.logging import configure_logging


def create_app(container: Container | None = None) -> FastAPI:
    owned_container = container or build_container()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = owned_container
        await owned_container.load_generated_strategies()
        yield
        await owned_container.close()

    app = FastAPI(
        title="Crypto Strategy Lab API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.container = owned_container
    configure_logging(owned_container.settings.log_level)
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(market_data_router)
    app.include_router(strategies_router)
    app.include_router(strategy_generation_router)
    app.include_router(market_data_websocket_router)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> JSONResponse:
        return JSONResponse({"status": "UP"})

    @app.get("/health/ready", include_in_schema=False)
    async def ready(request: Request) -> JSONResponse:
        healthy = await request.app.state.container.repository.ping()
        return JSONResponse(
            {"status": "UP" if healthy else "DOWN"},
            status_code=200 if healthy else 503,
        )

    return app


app = create_app()
