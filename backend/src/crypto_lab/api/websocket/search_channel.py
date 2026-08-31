from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from crypto_lab.application.search_service import search_run_payload

router = APIRouter()


@router.websocket("/ws/v1/search-runs/{run_id}")
async def search_progress(websocket: WebSocket, run_id: UUID) -> None:
    container = websocket.app.state.container
    await websocket.accept()
    row = await container.search_repository.get(run_id)
    if row is None:
        await websocket.close(code=4404, reason="search run not found")
        return
    await websocket.send_json(
        {"eventType": "SEARCH_PROGRESS", "version": 1, "payload": search_run_payload(row)}
    )
    queue = container.search_hub.subscribe(run_id)
    try:
        while True:
            await websocket.send_json(await queue.get())
    except WebSocketDisconnect:
        pass
    finally:
        container.search_hub.unsubscribe(run_id, queue)
