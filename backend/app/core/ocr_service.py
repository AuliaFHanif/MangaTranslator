"""OCR Service — runs Manga-OCR on detected speech bubbles.

Takes an image path + list of BubbleBox objects from the detection service.
Returns a list of OcrResult objects, one per bubble, with the extracted text.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from app.core.detection_service import BubbleBox

logger = logging.getLogger(__name__)


@dataclass
class OcrResult:
    bubble: BubbleBox
    text: str
    # Raw text before any cleanup
    raw_text: str = field(default="")

    def to_dict(self) -> dict:
        return {
            "box": self.bubble.to_dict(),
            "text": self.text,
            "raw_text": self.raw_text,
        }


class OcrService:
    # Minimum number of characters to keep a result — filters blank/noise crops
    MIN_TEXT_LENGTH = 1

    def run(self, image_path: str, bubbles: list[BubbleBox]) -> list[OcrResult]:
        """
        Run Manga-OCR on each detected bubble in the image.

        Args:
            image_path: Absolute path to the manga page image.
            bubbles: List of BubbleBox objects from the detection service.

        Returns:
            List of OcrResult objects in the same order as input bubbles.
            Bubbles that produce no text are excluded.
        """
        from app.core.model_manager import model_manager

        if not model_manager.is_loaded:
            raise RuntimeError("Models not loaded. Call model_manager.load() first.")

        if not bubbles:
            logger.debug("No bubbles to OCR.")
            return []

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.debug(f"Running OCR on {len(bubbles)} bubbles in {path.name}")

        image = Image.open(path).convert("RGB")
        results: list[OcrResult] = []

        for i, bubble in enumerate(bubbles):
            try:
                crop = bubble.crop(image)

                # Manga-OCR expects a PIL image
                raw_text = model_manager.ocr(crop)
                cleaned = self._clean(raw_text)

                if len(cleaned) >= self.MIN_TEXT_LENGTH:
                    results.append(OcrResult(
                        bubble=bubble,
                        text=cleaned,
                        raw_text=raw_text,
                    ))
                    logger.debug(f"  Bubble {i}: {repr(cleaned)}")
                else:
                    logger.debug(f"  Bubble {i}: skipped (empty)")

            except Exception as e:
                # Don't let a single bad crop kill the whole page
                logger.warning(f"  Bubble {i}: OCR failed — {e}")
                continue

        logger.debug(f"OCR complete: {len(results)}/{len(bubbles)} bubbles have text")
        return results

    def _clean(self, text: str) -> str:
        """Basic cleanup of raw OCR output."""
        if not text:
            return ""
        # Strip leading/trailing whitespace
        text = text.strip()
        # Collapse multiple spaces
        text = " ".join(text.split())
        return text


# Global singleton
ocr_service = OcrService()