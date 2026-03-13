"""Pipeline API — start/stop the pipeline and stream status via WebSocket."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.pipeline_worker import pipeline_worker
from app.models.project import Project

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── WebSocket connection manager ─────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self._clients: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.append(ws)
        logger.info(f"WebSocket client connected. Total: {len(self._clients)}")

    def disconnect(self, ws: WebSocket) -> None:
        self._clients = [c for c in self._clients if c is not ws]
        logger.info(f"WebSocket client disconnected. Total: {len(self._clients)}")

    async def broadcast(self, message: dict) -> None:
        if not self._clients:
            return
        text = json.dumps(message)
        dead: list[WebSocket] = []
        for client in self._clients:
            try:
                await client.send_text(text)
            except Exception:
                dead.append(client)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


# ─── Wire the worker to the broadcast function on first request ───────────────

def _ensure_worker_wired() -> None:
    """Give the pipeline worker a reference to the broadcast fn + event loop."""
    loop = asyncio.get_event_loop()
    pipeline_worker.set_broadcast(manager.broadcast, loop)


# ─── Request / Response schemas ───────────────────────────────────────────────

class StartPipelineRequest(BaseModel):
    folder_path: str


class PipelineStatusResponse(BaseModel):
    is_running: bool
    queue_depth: int
    active_page_index: int | None


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/start")
async def start_pipeline(req: StartPipelineRequest) -> dict:
    """Enqueue all pending pages and start the worker."""
    _ensure_worker_wired()

    folder = Path(req.folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {req.folder_path}")

    if not Project.exists(req.folder_path):
        raise HTTPException(status_code=404, detail="No project.json found. Open the folder first.")

    count = pipeline_worker.enqueue_project(req.folder_path)
    pipeline_worker.start()

    return {"enqueued": count, "is_running": pipeline_worker.is_running}


@router.post("/stop")
async def stop_pipeline() -> dict:
    """Signal the worker to stop after the current page finishes."""
    pipeline_worker.stop()
    return {"stopped": True}


@router.get("/status", response_model=PipelineStatusResponse)
async def pipeline_status() -> PipelineStatusResponse:
    active = pipeline_worker.active_job
    return PipelineStatusResponse(
        is_running=pipeline_worker.is_running,
        queue_depth=pipeline_worker.queue_depth,
        active_page_index=active[1] if active else None,
    )


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint — clients connect here to receive live page updates."""
    _ensure_worker_wired()
    await manager.connect(ws)
    try:
        # Send current pipeline status immediately on connect
        await ws.send_text(json.dumps({
            "type": "connected",
            "is_running": pipeline_worker.is_running,
            "queue_depth": pipeline_worker.queue_depth,
        }))
        # Keep the connection alive — worker broadcasts do the rest
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)