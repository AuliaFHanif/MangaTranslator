"""Model Manager — loads and holds YOLOv10 + Manga-OCR in VRAM.

Call `model_manager.load()` once on app startup.
Then access models via `model_manager.detector` and `model_manager.ocr`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import torch

logger = logging.getLogger(__name__)

# Where we store downloaded weights
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
YOLO_WEIGHTS = MODELS_DIR / "bubble_detector.pt"

# HuggingFace repo for the manga bubble detection weights
HF_REPO = "kitsumed/yolov8m_seg-speech-bubble"
HF_FILENAME = "model.pt"


class ModelManager:
    def __init__(self) -> None:
        self.detector = None   # YOLOv10 / Ultralytics model
        self.ocr = None        # MangaOcr model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._loaded = False

    def load(self) -> None:
        """Download weights if needed, then load both models into VRAM."""
        if self._loaded:
            return

        MODELS_DIR.mkdir(exist_ok=True)
        logger.info(f"Using device: {self.device}")

        self._load_detector()
        self._load_ocr()
        self._loaded = True
        logger.info("All models loaded and ready.")

    def _load_detector(self) -> None:
        from ultralytics import YOLO

        if not YOLO_WEIGHTS.exists():
            logger.info("Downloading bubble detector weights from HuggingFace...")
            from huggingface_hub import hf_hub_download
            from app.core.config import settings
            path = hf_hub_download(
                repo_id=HF_REPO,
                filename=HF_FILENAME,
                local_dir=MODELS_DIR,
                token=settings.hf_token,
            )
            # Move to expected location
            import shutil
            shutil.copy(path, YOLO_WEIGHTS)
            logger.info(f"Weights saved to {YOLO_WEIGHTS}")

        logger.info("Loading bubble detector...")
        self.detector = YOLO(str(YOLO_WEIGHTS))
        self.detector.to(self.device)
        logger.info("Bubble detector ready.")

    def _load_ocr(self) -> None:
        logger.info("Loading Manga-OCR (first run downloads ~400MB)...")
        from manga_ocr import MangaOcr
        # MangaOcr handles its own HuggingFace download internally
        self.ocr = MangaOcr()
        logger.info("Manga-OCR ready.")

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# Global singleton
model_manager = ModelManager()