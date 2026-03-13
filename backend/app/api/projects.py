"""Projects API — Phase 1 implementation."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.core.project_service import load_or_create_project
from app.models.project import Project

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Request / Response schemas ───────────────────────────────────────────────

class OpenProjectRequest(BaseModel):
    folder_path: str


class OpenProjectResponse(BaseModel):
    project: Project
    was_created: bool


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/open", response_model=OpenProjectResponse)
async def open_project(req: OpenProjectRequest) -> OpenProjectResponse:
    """
    Open or create a project from a folder path.
    Called after the user picks a folder via the OS dialog.
    """
    logger.info("[projects.open] request received for %s", req.folder_path)
    folder = Path(req.folder_path)
    if not folder.exists():
        logger.warning("[projects.open] folder does not exist: %s", req.folder_path)
        raise HTTPException(status_code=404, detail=f"Folder not found: {req.folder_path}")
    if not folder.is_dir():
        logger.warning("[projects.open] path is not a directory: %s", req.folder_path)
        raise HTTPException(status_code=400, detail="Path must be a directory")

    try:
        project, was_created = load_or_create_project(req.folder_path)
    except ValueError as e:
        logger.warning("[projects.open] failed for %s: %s", req.folder_path, e)
        raise HTTPException(status_code=400, detail=str(e)) from e

    logger.info(
        "[projects.open] completed for %s (created=%s, pages=%s)",
        req.folder_path,
        was_created,
        len(project.pages),
    )
    return OpenProjectResponse(project=project, was_created=was_created)


@router.get("/{project_id}/pages/{page_index}/thumbnail")
async def get_page_thumbnail(project_id: str, page_index: int, folder_path: str):
    """Serve the raw image for a page so the frontend can display thumbnails."""
    folder = Path(folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail="Project folder not found")

    try:
        project = Project.load(folder_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail="project.json not found") from e

    if page_index >= len(project.pages):
        raise HTTPException(status_code=404, detail="Page index out of range")

    page = project.pages[page_index]
    image_path = folder / page.raw_path

    if not image_path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {page.raw_path}")

    # Use StreamingResponse to ensure CORS headers are properly set
    def iterfile():
        with open(str(image_path), "rb") as f:
            yield from f

    media_type = "image/jpeg"
    if str(image_path).lower().endswith(".png"):
        media_type = "image/png"
    elif str(image_path).lower().endswith(".webp"):
        media_type = "image/webp"

    response = StreamingResponse(iterfile(), media_type=media_type)
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@router.get("/")
async def list_projects() -> dict:
    """Stub — recent projects list comes in Phase 1.5."""
    return {"projects": []}