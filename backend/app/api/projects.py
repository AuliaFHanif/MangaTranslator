"""Projects API — Phase 1 implementation."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.project_service import load_or_create_project
from app.models.project import Project

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
    """Open or create a project from a folder path."""
    folder = Path(req.folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {req.folder_path}")
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail="Path must be a directory")

    try:
        project, was_created = load_or_create_project(req.folder_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return OpenProjectResponse(project=project, was_created=was_created)


@router.get("/{project_id}/pages/{page_index}/thumbnail")
async def get_page_thumbnail(project_id: str, page_index: int, folder_path: str):
    """Serve the raw original image for a page."""
    project = Project.load(folder_path)
    page = next((p for p in project.pages if p.index == page_index), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    image_path = Path(page.raw_path)
    if not image_path.is_absolute():
        image_path = Path(folder_path) / image_path

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(str(image_path))


@router.get("/{project_id}/pages/{page_index}/final")
async def get_page_final(project_id: str, page_index: int, folder_path: str):
    """Serve the final typeset image for a completed page."""
    project = Project.load(folder_path)
    page = next((p for p in project.pages if p.index == page_index), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")

    if not page.final_path:
        raise HTTPException(status_code=404, detail="Final image not yet generated")

    final_path = Path(page.final_path)
    if not final_path.is_absolute():
        final_path = Path(folder_path) / final_path

    if not final_path.exists():
        raise HTTPException(status_code=404, detail="Final image file not found on disk")

    return FileResponse(str(final_path))