"""Inpainting Service — erases Japanese text from speech bubbles.

For each detected bubble box:
1. Creates a mask (white = inpaint, black = keep)
2. Runs LaMa inpainting to fill the masked area with background texture
3. Returns a clean PIL image ready for typesetting
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

logger = logging.getLogger(__name__)


class InpaintingService:
    # Shrink the mask slightly inside the bubble box to avoid painting over borders
    MASK_PADDING = 6

    def __init__(self) -> None:
        self._lama = None

    def _get_lama(self):
        if self._lama is None:
            from simple_lama_inpainting import SimpleLama
            logger.info("Loading LaMa inpainting model...")
            self._lama = SimpleLama()
            logger.info("LaMa ready.")
        return self._lama

    def clean_page(
        self,
        image_path: str,
        boxes: list[dict],
    ) -> Image.Image:
        """
        Remove Japanese text from all bubble regions on a page.

        Args:
            image_path: Path to the original manga page image.
            boxes: List of box dicts with x1, y1, x2, y2 keys (from page data).

        Returns:
            Clean PIL Image with text regions inpainted.
        """
        image = Image.open(image_path).convert("RGB")

        if not boxes:
            logger.debug("No boxes to inpaint.")
            return image

        # Build a single mask for all bubbles at once
        mask = self._build_mask(image.size, boxes)

        # If mask is empty (all boxes were too small), return original
        if not np.any(np.array(mask) > 0):
            logger.debug("Mask is empty, skipping inpainting.")
            return image

        logger.debug(f"Running LaMa inpainting on {len(boxes)} bubbles...")
        lama = self._get_lama()
        result = lama(image, mask)

        # LaMa returns a PIL Image
        if not isinstance(result, Image.Image):
            result = Image.fromarray(result)

        logger.debug("Inpainting complete.")
        return result.convert("RGB")

    def _build_mask(
        self,
        image_size: tuple[int, int],
        boxes: list[dict],
    ) -> Image.Image:
        """
        Build a grayscale mask image.
        White (255) = inpaint this area.
        Black (0)   = keep this area.
        """
        mask = Image.new("L", image_size, 0)
        draw = ImageDraw.Draw(mask)

        for box in boxes:
            x1 = box["x1"] + self.MASK_PADDING
            y1 = box["y1"] + self.MASK_PADDING
            x2 = box["x2"] - self.MASK_PADDING
            y2 = box["y2"] - self.MASK_PADDING

            # Skip if padding made the box invalid
            if x2 <= x1 or y2 <= y1:
                continue

            draw.rectangle([x1, y1, x2, y2], fill=255)

        # Slight blur on mask edges for smoother blending
        mask = mask.filter(ImageFilter.GaussianBlur(radius=2))

        return mask


# Global singleton
inpainting_service = InpaintingService()