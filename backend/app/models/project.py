"""Project and Page data models."""

from __future__ import annotations
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class PageStatus(str, Enum):
    PENDING = "pending"
    DETECTING = "detecting"
    OCR = "ocr"
    TRANSLATING = "translating"
    INPAINTING = "inpainting"
    TYPESETTING = "typesetting"
    REVIEW = "review"
    DONE = "done"
    ERROR = "error"


class PageRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    index: int
    filename: str
    raw_path: str
    clean_path: str | None = None
    final_path: str | None = None
    data_path: str | None = None
    status: PageStatus = PageStatus.PENDING
    error_message: str | None = None


class ProjectSettings(BaseModel):
    source_language: str = "ja"
    target_language: str = "en"
    lmstudio_model: str | None = None
    persona_prompt: str | None = None
    max_concurrent_pages: int = 2


class Project(BaseModel):
    version: str = "1.0.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    folder_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    pages: list[PageRecord] = Field(default_factory=list)

    def save(self) -> None:
        """Write project.json to the project folder."""
        self.updated_at = datetime.now(timezone.utc)
        project_file = Path(self.folder_path) / "project.json"
        project_file.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, folder_path: str) -> Project:
        """Load project.json from a folder."""
        project_file = Path(folder_path) / "project.json"
        return cls.model_validate_json(project_file.read_text(encoding="utf-8"))

    @classmethod
    def exists(cls, folder_path: str) -> bool:
        return (Path(folder_path) / "project.json").exists()