"""Pipeline Worker — background thread that processes manga pages.

Pulls pages off a queue and runs them through:
  detecting → ocr → pending_translation

Results are saved to data/<page_id>.json and project.json is updated
after each page so progress is never lost.

Status updates are broadcast to all connected WebSocket clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from pathlib import Path
from queue import Empty, Queue
from typing import TYPE_CHECKING

from app.core.detection_service import detection_service
from app.core.ocr_service import ocr_service
from app.models.project import PageStatus, Project

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PipelineWorker:
    def __init__(self) -> None:
        self._queue: Queue[tuple[str, int]] = Queue()  # (folder_path, page_index)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._active_job: tuple[str, int] | None = None
        self._lock = threading.Lock()

        # WebSocket broadcast callback — set by the API layer
        self._broadcast_fn = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ─── Public API ───────────────────────────────────────────────────────────

    def set_broadcast(self, fn, loop: asyncio.AbstractEventLoop) -> None:
        """Register the async broadcast function and its event loop."""
        self._broadcast_fn = fn
        self._loop = loop

    def enqueue_project(self, folder_path: str) -> int:
        """Add all pending pages of a project to the queue. Returns count enqueued."""
        project = Project.load(folder_path)
        project_root = Path(folder_path)
        count = 0
        recovered = 0
        for page in project.pages:
            status = str(page.model_dump(mode="json").get("status", "")).lower()

            # Allow retries for failed pages without forcing project recreation.
            if status in (PageStatus.PENDING.value, PageStatus.ERROR.value):
                self._queue.put((folder_path, page.index))
                count += 1
                continue

            # Recovery path: if a page says "translating" but OCR data is missing
            # or malformed (from an older failed run), rerun OCR for that page.
            if status == PageStatus.TRANSLATING.value and self._needs_ocr_recovery(
                project_root, page.data_path
            ):
                self._queue.put((folder_path, page.index))
                count += 1
                recovered += 1

        # Safety net: if nothing was enqueued, recover any page whose OCR output
        # file is missing or invalid, regardless of current status.
        if count == 0:
            for page in project.pages:
                if self._needs_ocr_recovery(project_root, page.data_path):
                    self._queue.put((folder_path, page.index))
                    count += 1
                    recovered += 1
        if recovered:
            logger.info(
                "Enqueued %s pages from %s (%s recovered translating pages)",
                count,
                folder_path,
                recovered,
            )
        else:
            logger.info(f"Enqueued {count} pages from {folder_path}")
        return count

    def _needs_ocr_recovery(self, project_root: Path, data_path: str | None) -> bool:
        """Return True when OCR output for a page is missing or invalid."""
        if not data_path:
            return True

        output_path = project_root / data_path
        if not output_path.exists():
            return True

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            return True

        return not isinstance(payload.get("bubbles"), list)

    def start(self) -> None:
        """Start the worker thread if not already running."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run, daemon=True, name="pipeline-worker"
            )
            self._thread.start()
            logger.info("Pipeline worker started.")

    def stop(self) -> None:
        """Signal the worker to stop after the current page finishes."""
        self._stop_event.set()
        logger.info("Pipeline worker stop requested.")

    @property
    def is_running(self) -> bool:
        # Treat "running" as actively processing/queued work, not idle thread state.
        return bool(self._active_job is not None or not self._queue.empty())

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    @property
    def active_job(self) -> tuple[str, int] | None:
        return self._active_job

    # ─── Worker loop ──────────────────────────────────────────────────────────

    def _run(self) -> None:
        logger.info("Pipeline worker loop running.")
        while not self._stop_event.is_set():
            try:
                folder_path, page_index = self._queue.get(timeout=1.0)
            except Empty:
                continue

            self._active_job = (folder_path, page_index)
            try:
                self._process_page(folder_path, page_index)
            except Exception as e:
                logger.error(f"Unhandled error on page {page_index}: {e}", exc_info=True)
                self._mark_error(folder_path, page_index, str(e))
            finally:
                self._active_job = None
                self._queue.task_done()

        logger.info("Pipeline worker loop exited.")

    def _process_page(self, folder_path: str, page_index: int) -> None:
        project = Project.load(folder_path)
        page = next((p for p in project.pages if p.index == page_index), None)
        if page is None:
            logger.warning(f"Page {page_index} not found in project.")
            return

        project_root = Path(folder_path)
        image_path = project_root / page.raw_path
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        data_dir = Path(folder_path) / "data"
        data_dir.mkdir(exist_ok=True)

        # Prefer the page-level data path from project.json for stable naming.
        if page.data_path:
            output_path = project_root / page.data_path
        else:
            output_path = data_dir / f"{page.id}.json"
            page.data_path = str(output_path.relative_to(project_root))
            project.save()

        # ── Stage 1: Detection ────────────────────────────────────────────────
        self._set_status(folder_path, page_index, PageStatus.DETECTING)

        bubbles = detection_service.detect(str(image_path))
        logger.info(f"Page {page_index}: detected {len(bubbles)} bubbles")

        # ── Stage 2: OCR ──────────────────────────────────────────────────────
        self._set_status(folder_path, page_index, PageStatus.OCR)

        ocr_results = ocr_service.run(str(image_path), bubbles)
        logger.info(f"Page {page_index}: OCR produced {len(ocr_results)} text blocks")

        # ── Save results ──────────────────────────────────────────────────────
        page_data = {
            "page_id": page.id,
            "page_index": page_index,
            "image_path": str(image_path),
            "bubbles": [r.to_dict() for r in ocr_results],
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(page_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"Page {page_index}: saved results to {output_path.name}")

        # ── Advance status ────────────────────────────────────────────────────
        self._set_status(folder_path, page_index, PageStatus.TRANSLATING)

    def _set_status(
        self, folder_path: str, page_index: int, status: PageStatus
    ) -> None:
        """Update page status in project.json and broadcast to WebSocket clients."""
        project = Project.load(folder_path)
        for page in project.pages:
            if page.index == page_index:
                page.status = status
                break
        project.save()

        self._broadcast({
            "type": "page_status",
            "folder_path": folder_path,
            "page_index": page_index,
            "status": status.value,
        })

    def _mark_error(self, folder_path: str, page_index: int, message: str) -> None:
        try:
            project = Project.load(folder_path)
            for page in project.pages:
                if page.index == page_index:
                    page.status = PageStatus.ERROR
                    page.error_message = message
                    break
            project.save()
        except Exception as e:
            logger.error(f"Failed to mark error on page {page_index}: {e}")

        self._broadcast({
            "type": "page_status",
            "folder_path": folder_path,
            "page_index": page_index,
            "status": "error",
            "error": message,
        })

    def _broadcast(self, message: dict) -> None:
        """Fire-and-forget broadcast to all WebSocket clients."""
        if self._broadcast_fn is None or self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_fn(message), self._loop
            )
        except Exception as e:
            logger.warning(f"Broadcast failed: {e}")


# Global singleton
pipeline_worker = PipelineWorker()