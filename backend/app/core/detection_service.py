"""Detection Service — runs the bubble detector on a manga page.

Returns a list of bounding boxes for detected speech bubbles.
Each box is (x1, y1, x2, y2) in pixel coordinates, plus a confidence score.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class BubbleBox:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "confidence": round(self.confidence, 4),
        }

    def crop(self, image: Image.Image) -> Image.Image:
        """Crop this bounding box out of a PIL image."""
        return image.crop((self.x1, self.y1, self.x2, self.y2))


class DetectionService:
    # Only keep bubbles above this confidence threshold
    CONFIDENCE_THRESHOLD = 0.35

    # Ignore tiny boxes (likely noise) — min area in pixels
    MIN_AREA = 500

    def detect(self, image_path: str) -> list[BubbleBox]:
        """
        Run bubble detection on a manga page image.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            List of BubbleBox objects sorted top-to-bottom, left-to-right.
        """
        from app.core.model_manager import model_manager

        if not model_manager.is_loaded:
            raise RuntimeError("Models not loaded. Call model_manager.load() first.")

        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.debug(f"Running detection on {path.name}")

        # Run inference — ultralytics returns a list of Results objects
        results = model_manager.detector(
            str(path),
            conf=self.CONFIDENCE_THRESHOLD,
            verbose=False,
        )

        boxes: list[BubbleBox] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])

                bubble = BubbleBox(
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                    confidence=conf,
                )

                if bubble.area >= self.MIN_AREA:
                    boxes.append(bubble)

        # Sort top-to-bottom, left-to-right (natural reading order for LTR)
        # For manga (RTL) this still gives a consistent ordering per page
        boxes.sort(key=lambda b: (b.y1 // 50, b.x1))

        logger.debug(f"Detected {len(boxes)} bubbles in {path.name}")
        return boxes


# Global singleton
detection_service = DetectionService()