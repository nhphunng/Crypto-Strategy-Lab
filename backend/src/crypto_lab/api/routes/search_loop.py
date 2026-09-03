"""REST boundary for observing and controlling the background search loop."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from crypto_lab.api.common import SuccessEnvelope, success_envelope
from crypto_lab.api.middleware import request_id
from crypto_lab.api.schemas.search_loop import SearchLoopStatusDto, stats_to_dto
from crypto_lab.application.evaluations.auto_evaluate import SearchLoopRunner

router = APIRouter(prefix="/api/v1/search-loop", tags=["search-loop"])


def _runner(request: Request) -> SearchLoopRunner:
    container = request.app.state.container
    runner = getattr(container, "search_loop", None)
    if not isinstance(runner, SearchLoopRunner):
        raise HTTPException(
            503,
            {
                "code": "SEARCH_LOOP_UNAVAILABLE",
                "message": "The background search loop is not enabled on this deployment.",
            },
        )
    return runner


@router.get("/status", response_model=SuccessEnvelope[SearchLoopStatusDto])
async def get_search_loop_status(request: Request) -> SuccessEnvelope[SearchLoopStatusDto]:
    runner = _runner(request)
    return success_envelope(
        stats_to_dto(await runner.snapshot()), "Search loop status loaded.", request_id(request)
    )


@router.post("/pause", response_model=SuccessEnvelope[SearchLoopStatusDto])
async def pause_search_loop(request: Request) -> SuccessEnvelope[SearchLoopStatusDto]:
    runner = _runner(request)
    runner.pause()
    return success_envelope(
        stats_to_dto(await runner.snapshot()), "Search loop paused.", request_id(request)
    )


@router.post("/resume", response_model=SuccessEnvelope[SearchLoopStatusDto])
async def resume_search_loop(request: Request) -> SuccessEnvelope[SearchLoopStatusDto]:
    runner = _runner(request)
    runner.resume()
    return success_envelope(
        stats_to_dto(await runner.snapshot()), "Search loop resumed.", request_id(request)
    )


__all__ = ["router"]
