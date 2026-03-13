"""Translation Service — sends Japanese bubble text to LM Studio.

Sends all bubbles from a page in a single request for better context.
Returns translated English strings in the same order as input.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# LM Studio runs an OpenAI-compatible API on this port by default
LMSTUDIO_BASE = "http://127.0.0.1:1234/v1"
TIMEOUT = 120.0  # seconds — 14B model can be slow on first token

SYSTEM_PROMPT = """/no_think
You are a professional manga translator. Translate Japanese speech bubble text into natural, fluent English that reads like a native English manga localization.

Rules:
- Translate each line naturally — prioritize how it sounds in English, not word-for-word accuracy
- Keep ellipses (．．．), ellipsis variants, and sound effects exactly as-is
- Keep single punctuation marks (、。！？) as-is if they appear alone
- Do not add explanations, notes, or romanization
- Return ONLY a valid JSON array of strings, one per input line, in the same order
- The array must have exactly the same number of elements as the input"""

USER_TEMPLATE = """Translate these speech bubbles from the same manga page. They appear in reading order.

Input JSON array:
{input_json}

Return only the translated JSON array, nothing else."""


class TranslationService:
    def translate_page(self, texts: list[str]) -> list[str]:
        """
        Translate a list of Japanese bubble texts from a single manga page.

        Args:
            texts: List of Japanese strings in reading order.

        Returns:
            List of English strings in the same order.
            Falls back to original text if translation fails.
        """
        if not texts:
            return []

        # Filter out texts that don't need translation (lone punctuation etc.)
        # but keep their positions so we can reassemble
        to_translate: list[tuple[int, str]] = []
        results: list[str] = list(texts)  # start with originals as fallback

        for i, text in enumerate(texts):
            if self._needs_translation(text):
                to_translate.append((i, text))

        if not to_translate:
            logger.debug("No texts need translation on this page.")
            return results

        indices, japanese = zip(*to_translate)
        logger.debug(f"Translating {len(japanese)} bubbles via LM Studio...")

        try:
            translated = self._call_lmstudio(list(japanese))
            if len(translated) == len(japanese):
                for idx, english in zip(indices, translated):
                    results[idx] = english
            else:
                logger.warning(
                    f"LM Studio returned {len(translated)} translations "
                    f"for {len(japanese)} inputs — using originals as fallback."
                )
        except Exception as e:
            logger.error(f"Translation failed: {e}")
            # Return originals — pipeline continues, page won't be stuck

        return results

    def _call_lmstudio(self, texts: list[str]) -> list[str]:
        """Call LM Studio's OpenAI-compatible chat completions endpoint."""
        payload: dict[str, Any] = {
            "model": "local-model",  # LM Studio ignores this, uses loaded model
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": USER_TEMPLATE.format(
                        input_json=json.dumps(texts, ensure_ascii=False, indent=2)
                    ),
                },
            ],
            "temperature": 0.3,   # Low temp for consistent translation
            "max_tokens": 2048,
            "stream": False,
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(
                f"{LMSTUDIO_BASE}/chat/completions",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        raw = data["choices"][0]["message"]["content"].strip()
        logger.debug(f"LM Studio raw response: {raw[:200]}")

        return self._parse_response(raw, expected_count=len(texts))

    def _parse_response(self, raw: str, expected_count: int) -> list[str]:
        """Extract a JSON array from the model response."""
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
        raw = raw.strip()

        # Find the first JSON array in the response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            raw = match.group(0)

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
                return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LM Studio response as JSON: {e}")
            logger.warning(f"Raw response was: {raw[:500]}")

        # Last resort — split by newlines if JSON parsing fails
        lines = [l.strip().strip('"') for l in raw.splitlines() if l.strip()]
        if len(lines) == expected_count:
            logger.warning("Fell back to newline splitting for translation output.")
            return lines

        raise ValueError(f"Could not parse translation response: {raw[:200]}")

    def _needs_translation(self, text: str) -> bool:
        """Return False for texts that are just punctuation or very short noise."""
        stripped = text.strip()
        if not stripped:
            return False
        # Single character — punctuation, ellipsis, comma etc.
        if len(stripped) <= 1:
            return False
        # Only dots/ellipses/punctuation
        if re.fullmatch(r"[．。、・…\.\s]+", stripped):
            return False
        return True


# Global singleton
translation_service = TranslationService()