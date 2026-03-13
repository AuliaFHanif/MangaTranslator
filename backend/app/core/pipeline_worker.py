"""Pipeline Worker — background thread that processes manga pages.

Pulls pages off a queue and runs them through:
    detecting → ocr → translating → inpainting → typesetting → done

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
from app.core.inpainting_service import inpainting_service
from app.core.ocr_service import ocr_service
from app.core.translation_service import translation_service
from app.core.typesetting_service import typesetting_service
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
        """Add unfinished/resumable pages of a project to the queue."""
        project = Project.load(folder_path)
        project_root = Path(folder_path)
        count = 0
        recovered = 0

        for page in project.pages:
            status = str(page.model_dump(mode="json").get("status", "")).lower()

            if status in (
                PageStatus.PENDING.value,
                PageStatus.DETECTING.value,
                PageStatus.OCR.value,
                PageStatus.ERROR.value,
                PageStatus.TRANSLATING.value,
                PageStatus.INPAINTING.value,
                PageStatus.TYPESETTING.value,
            ):
                self._queue.put((folder_path, page.index))
                count += 1

        # Safety net: if nothing was enqueued, recover pages with missing/invalid
        # data or incomplete translation regardless of current status.
        if count == 0:
            for page in project.pages:
                if self._needs_processing_recovery(project_root, page):
                    self._queue.put((folder_path, page.index))
                    count += 1
                    recovered += 1

        if recovered:
            logger.info(
                "Enqueued %s pages from %s (%s recovered pages)",
                count,
                folder_path,
                recovered,
            )
        else:
            logger.info(f"Enqueued {count} pages from {folder_path}")

        return count

    def _needs_processing_recovery(self, project_root: Path, page) -> bool:
        """Return True when page data or final output is missing/incomplete."""
        if not page.data_path:
            return True

        output_path = project_root / page.data_path
        if not output_path.exists():
            return True

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            return True

        bubbles = payload.get("bubbles")
        if not isinstance(bubbles, list):
            return True

        status = str(page.model_dump(mode="json").get("status", "")).lower()
        if status == PageStatus.TRANSLATING.value:
            return any(not isinstance(b.get("translation"), str) for b in bubbles)

        if status in (PageStatus.INPAINTING.value, PageStatus.TYPESETTING.value):
            if not page.final_path:
                return True
            return not (project_root / page.final_path).exists()

        return False

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
                logger.error(
                    f"Unhandled error on page {page_index}: {e}",
                    exc_info=True,
                )
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

        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        assets_dir = project_root / "assets"
        assets_dir.mkdir(exist_ok=True)

        # Prefer the page-level data path from project.json for stable naming.
        if page.data_path:
            output_path = project_root / page.data_path
        else:
            output_path = data_dir / f"{page.id}.json"
            page.data_path = str(output_path.relative_to(project_root))
            project.save()

        final_rel_path = page.final_path or f"assets/{page.id}_final.png"
        final_path = project_root / final_rel_path

        # Load existing page data to allow resuming from translating state.
        existing_data: dict = {}
        if output_path.exists():
            try:
                existing_data = json.loads(output_path.read_text(encoding="utf-8"))
            except Exception:
                existing_data = {}

        status = str(page.model_dump(mode="json").get("status", "")).lower()
        ocr_results_data = existing_data.get("bubbles", [])

        # ── Stage 1/2: Detection + OCR ───────────────────────────────────────
        if status in (
            PageStatus.PENDING.value,
            PageStatus.DETECTING.value,
            PageStatus.OCR.value,
            PageStatus.ERROR.value,
        ) or not isinstance(ocr_results_data, list):
            self._set_status(folder_path, page_index, PageStatus.DETECTING)

            bubbles = detection_service.detect(str(image_path))
            logger.info(f"Page {page_index}: detected {len(bubbles)} bubbles")

            self._set_status(folder_path, page_index, PageStatus.OCR)

            ocr_results = ocr_service.run(str(image_path), bubbles)
            logger.info(
                f"Page {page_index}: OCR produced {len(ocr_results)} text blocks"
            )
            ocr_results_data = [r.to_dict() for r in ocr_results]

            # Save after OCR so we can resume from translating if later stages fail.
            page_data = {
                "page_id": page.id,
                "page_index": page_index,
                "image_path": str(image_path),
                "bubbles": ocr_results_data,
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(page_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"Page {page_index}: saved OCR data to {output_path.name}")
            existing_data = page_data
            ocr_results_data = page_data["bubbles"]
            status = PageStatus.TRANSLATING.value
        elif status == PageStatus.TRANSLATING.value and isinstance(ocr_results_data, list):
            logger.info(f"Page {page_index}: skipping detection/OCR (already done)")

        # ── Stage 3: Translation ─────────────────────────────────────────────
        if status == PageStatus.TRANSLATING.value or any(
            not isinstance(b.get("translation"), str) for b in ocr_results_data
        ):
            self._set_status(folder_path, page_index, PageStatus.TRANSLATING)

            japanese_texts = [str(b.get("text", "")) for b in ocr_results_data]
            logger.info(f"Page {page_index}: translating {len(japanese_texts)} bubbles")

            translated_texts = translation_service.translate_page(japanese_texts)

            for i, bubble in enumerate(ocr_results_data):
                bubble["translation"] = (
                    translated_texts[i] if i < len(translated_texts) else ""
                )

            existing_data = {
                "page_id": page.id,
                "page_index": page_index,
                "image_path": str(image_path),
                "bubbles": ocr_results_data,
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(existing_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"Page {page_index}: saved translations to {output_path.name}")
            status = PageStatus.INPAINTING.value

        # ── Stage 4: Inpainting ──────────────────────────────────────────────
        clean_image = None
        if status == PageStatus.INPAINTING.value:
            self._set_status(folder_path, page_index, PageStatus.INPAINTING)

            boxes = [b["box"] for b in ocr_results_data]
            logger.info(f"Page {page_index}: inpainting {len(boxes)} bubble regions")
            clean_image = inpainting_service.clean_page(str(image_path), boxes)
            logger.info(f"Page {page_index}: inpainting complete")
            status = PageStatus.TYPESETTING.value

        # ── Stage 5: Typesetting ─────────────────────────────────────────────
        if status == PageStatus.TYPESETTING.value:
            self._set_status(folder_path, page_index, PageStatus.TYPESETTING)

            if clean_image is None:
                boxes = [b["box"] for b in ocr_results_data]
                clean_image = inpainting_service.clean_page(str(image_path), boxes)

            logger.info(f"Page {page_index}: typesetting translations")
            final_image = typesetting_service.typeset_page(clean_image, ocr_results_data)

            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_image.save(str(final_path), format="PNG", optimize=True)
            logger.info(f"Page {page_index}: saved final image to {final_path.name}")

            updated_project = Project.load(folder_path)
            for record in updated_project.pages:
                if record.index == page_index:
                    record.final_path = final_rel_path
                    break
            updated_project.save()

        # ── Done ─────────────────────────────────────────────────────────────
        self._set_status(folder_path, page_index, PageStatus.DONE)
        logger.info(f"Page {page_index}: done")

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