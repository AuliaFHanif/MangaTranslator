"""Project service — handles creation, loading, and folder scanning."""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from app.models.project import PageRecord, Project

logger = logging.getLogger(__name__)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def _natural_sort_key(path: Path) -> list[int | str]:
    """Sort filenames naturally: page_2 before page_10."""
    parts = re.split(r"(\d+)", path.name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def scan_folder(folder_path: str) -> list[Path]:
    """Return all image files in a folder sorted in natural order."""
    folder = Path(folder_path)
    logger.info("[project_service.scan_folder] scanning %s", folder_path)
    started_at = time.perf_counter()
    images = [p for p in folder.iterdir() if p.is_file() and _is_image(p)]
    logger.info(
        "[project_service.scan_folder] found %s image(s) in %.3fs",
        len(images),
        time.perf_counter() - started_at,
    )
    return sorted(images, key=_natural_sort_key)


def create_project(folder_path: str, name: str | None = None) -> Project:
    """
    Create a new project from a folder of images.
    Scans for images, builds PageRecords, writes project.json.
    """
    logger.info("[project_service.create_project] starting for %s", folder_path)
    started_at = time.perf_counter()
    folder = Path(folder_path)
    if not folder.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")

    project_name = name or folder.name
    images = scan_folder(folder_path)

    if not images:
        raise ValueError(f"No images found in: {folder_path}")

    # Create assets/ and data/ subdirectories
    (folder / "assets").mkdir(exist_ok=True)
    (folder / "data").mkdir(exist_ok=True)

    pages = [
        PageRecord(
            index=i,
            filename=img.name,
            raw_path=str(img.relative_to(folder)),
            data_path=f"data/page_{i:03d}.json",
        )
        for i, img in enumerate(images)
    ]

    project = Project(
        name=project_name,
        folder_path=str(folder),
        pages=pages,
    )
    project.save()
    logger.info(
        "[project_service.create_project] completed for %s with %s page(s) in %.3fs",
        folder_path,
        len(pages),
        time.perf_counter() - started_at,
    )
    return project


def _is_project_cache_valid(project: Project, folder_path: str) -> bool:
    """Validate that cached project metadata still matches files on disk."""
    folder = Path(folder_path)

    # Detect stale cache generated on a different runtime/path style.
    if Path(project.folder_path) != folder:
        return False

    # If any cached raw image path no longer exists, force a rescan/rebuild.
    for page in project.pages:
        if not (folder / page.raw_path).exists():
            return False

    return True


def load_or_create_project(folder_path: str) -> tuple[Project, bool]:
    """
    Load existing project.json if present, otherwise create a new one.
    Returns (project, was_created).
    """
    logger.info("[project_service.load_or_create] checking %s", folder_path)
    if Project.exists(folder_path):
        logger.info("[project_service.load_or_create] existing project.json found for %s", folder_path)
        project = Project.load(folder_path)
        if _is_project_cache_valid(project, folder_path):
            logger.info(
                "[project_service.load_or_create] cache valid for %s with %s page(s)",
                folder_path,
                len(project.pages),
            )
            return project, False
        logger.info("[project_service.load_or_create] cache invalid for %s, rebuilding", folder_path)
    else:
        logger.info("[project_service.load_or_create] no project.json found for %s, creating", folder_path)
    return create_project(folder_path), True