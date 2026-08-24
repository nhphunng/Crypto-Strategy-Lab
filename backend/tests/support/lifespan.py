"""Minimal ASGI lifespan runner so tests exercise real application startup."""

from __future__ import annotations

from types import TracebackType

from fastapi import FastAPI


class LifespanManager:
    def __init__(self, app: FastAPI) -> None:
        self._app = app
        self._context = app.router.lifespan_context(app)

    async def __aenter__(self) -> FastAPI:
        await self._context.__aenter__()
        return self._app

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._context.__aexit__(exc_type, exc, traceback)
