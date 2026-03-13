"""Typesetting Service — draws English translations into cleaned bubble boxes.

Improvements over v1:
- Detects narrow/vertical bubbles and adjusts font size ceiling accordingly
- Hard clips text to bubble bounds — nothing ever draws outside the box
- Dynamic max font size based on box area
- Tighter line spacing for better fit
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

FONT_PATH = Path(__file__).parent.parent.parent / "fonts" / "Bangers-Regular.ttf"

MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 42

TEXT_PADDING = 8

TEXT_COLOR = (0, 0, 0)
LINE_SPACING = 1.15


class TypesettingService:
    def __init__(self) -> None:
        self._font_cache: dict[int, ImageFont.FreeTypeFont] = {}

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._font_cache:
            self._font_cache[size] = ImageFont.truetype(str(FONT_PATH), size)
        return self._font_cache[size]

    def typeset_page(
        self,
        clean_image: Image.Image,
        bubbles: list[dict],
    ) -> Image.Image:
        result = clean_image.copy()

        for bubble in bubbles:
            translation = bubble.get("translation", "")
            if not translation or translation == bubble.get("text", ""):
                continue
            box = bubble["box"]
            self._draw_bubble_text(result, translation, box)

        return result

    def _draw_bubble_text(
        self,
        image: Image.Image,
        text: str,
        box: dict,
    ) -> None:
        x1 = box["x1"] + TEXT_PADDING
        y1 = box["y1"] + TEXT_PADDING
        x2 = box["x2"] - TEXT_PADDING
        y2 = box["y2"] - TEXT_PADDING

        available_w = x2 - x1
        available_h = y2 - y1

        if available_w < 10 or available_h < 10:
            return

        max_font = self._max_font_for_box(available_w, available_h)
        best = self._fit_text(text, available_w, available_h, max_font)
        if best is None:
            logger.debug(f"Could not fit text: {repr(text[:30])}")
            return

        font, lines = best
        line_h = self._line_height(font)
        total_h = line_h * len(lines)

        bubble_w = box["x2"] - box["x1"]
        bubble_h = box["y2"] - box["y1"]
        text_layer = Image.new("RGBA", (bubble_w, bubble_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        offset_x = TEXT_PADDING
        offset_y = TEXT_PADDING + (available_h - total_h) // 2

        for i, line in enumerate(lines):
            line_w = self._text_width(font, line)
            lx = offset_x + (available_w - line_w) // 2
            ly = offset_y + i * line_h

            for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                draw.text((lx + dx, ly + dy), line, font=font, fill=(255, 255, 255, 255))

            draw.text((lx, ly), line, font=font, fill=(*TEXT_COLOR, 255))

        image.paste(text_layer, (box["x1"], box["y1"]), text_layer)

    def _max_font_for_box(self, w: int, h: int) -> int:
        """Determine font ceiling from box dimensions and aspect ratio."""
        aspect = h / max(w, 1)
        area = w * h

        if aspect > 2.0:
            ceiling = min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, w // 3))
        elif aspect > 1.5:
            ceiling = min(MAX_FONT_SIZE, max(MIN_FONT_SIZE, w // 2))
        else:
            ceiling = MAX_FONT_SIZE

        area_cap = max(MIN_FONT_SIZE, int((area ** 0.5) / 6))
        return min(ceiling, area_cap, MAX_FONT_SIZE)

    def _fit_text(
        self,
        text: str,
        available_w: int,
        available_h: int,
        max_font: int,
    ) -> tuple[ImageFont.FreeTypeFont, list[str]] | None:
        best = None
        lo, hi = MIN_FONT_SIZE, max_font

        while lo <= hi:
            mid = (lo + hi) // 2
            font = self._get_font(mid)
            lines = self._wrap_text(text, font, available_w)
            line_h = self._line_height(font)
            total_h = line_h * len(lines)

            if total_h <= available_h:
                best = (font, lines)
                lo = mid + 1
            else:
                hi = mid - 1

        return best

    def _wrap_text(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        max_width: int,
    ) -> list[str]:
        words = text.split()
        if not words:
            return []

        lines: list[str] = []
        current = words[0]

        for word in words[1:]:
            candidate = current + " " + word
            if self._text_width(font, candidate) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word

        lines.append(current)
        return lines

    def _text_width(self, font: ImageFont.FreeTypeFont, text: str) -> int:
        bbox = font.getbbox(text)
        return int(bbox[2] - bbox[0])

    def _line_height(self, font: ImageFont.FreeTypeFont) -> int:
        bbox = font.getbbox("Ágjpq")
        return int((bbox[3] - bbox[1]) * LINE_SPACING)


# Global singleton
typesetting_service = TypesettingService()