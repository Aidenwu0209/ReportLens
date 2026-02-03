"""T8 – PaddleOCR-VL 1.5 Adapter.

Input:  page image path
Output: standardised blocks[] with { text, bbox:[x0,y0,x1,y1], conf, type }
        bbox normalised to [0, 1] (pixel-independent highlighting)

Resilience: exponential backoff retry (429 / 5xx), circuit breaker on
consecutive failures.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Circuit-breaker state ────────────────────────────────
_consecutive_failures = 0
_CIRCUIT_THRESHOLD = 5
_circuit_open_until = 0.0


class OcrBlock:
    """Normalised OCR block."""

    def __init__(self, text: str, bbox: list[float], conf: float, block_type: str = "text"):
        self.text = text
        self.bbox = bbox  # [x0, y0, x1, y1] ∈ [0, 1]
        self.conf = conf
        self.block_type = block_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "conf": self.conf,
            "type": self.block_type,
        }


def _normalise_bbox(bbox: list, width: int, height: int) -> list[float]:
    """Convert pixel bbox to normalised [0,1] coords."""
    if not bbox or len(bbox) < 4:
        return [0.0, 0.0, 0.0, 0.0]
    x0, y0, x1, y1 = bbox[:4]
    return [
        round(x0 / max(width, 1), 6),
        round(y0 / max(height, 1), 6),
        round(x1 / max(width, 1), 6),
        round(y1 / max(height, 1), 6),
    ]


async def ocr_page(image_path: str, width: int, height: int) -> list[dict[str, Any]]:
    """Call PaddleOCR-VL 1.5 API for a single page image.

    Returns list of normalised block dicts.
    """
    global _consecutive_failures, _circuit_open_until

    # Circuit breaker check
    if _consecutive_failures >= _CIRCUIT_THRESHOLD:
        if time.time() < _circuit_open_until:
            raise RuntimeError("OCR circuit breaker OPEN – too many consecutive failures")
        # half-open: allow one attempt
        _consecutive_failures = _CIRCUIT_THRESHOLD - 1

    image_bytes = Path(image_path).read_bytes()
    b64 = base64.b64encode(image_bytes).decode()

    payload = {
        "image": b64,
        "language": "ch",
    }

    headers = {
        "Authorization": f"Bearer {settings.PADDLEOCR_VL_API_KEY}",
        "Content-Type": "application/json",
    }

    max_retries = 3
    backoff = 1.0

    async with httpx.AsyncClient(timeout=settings.PADDLEOCR_VL_TIMEOUT_SEC) as client:
        for attempt in range(max_retries + 1):
            try:
                resp = await client.post(
                    f"{settings.PADDLEOCR_VL_API_BASE}/ocr",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()

                result = resp.json()
                _consecutive_failures = 0

                blocks = []
                for item in result.get("result", result.get("blocks", [])):
                    text = item.get("text", "")
                    raw_bbox = item.get("bbox", item.get("position", []))
                    conf = item.get("confidence", item.get("conf", 0.0))
                    block_type = item.get("type", "text")

                    bbox_norm = _normalise_bbox(raw_bbox, width, height)
                    blocks.append(OcrBlock(text, bbox_norm, conf, block_type).to_dict())

                return blocks

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                _consecutive_failures += 1
                if _consecutive_failures >= _CIRCUIT_THRESHOLD:
                    _circuit_open_until = time.time() + 60
                if attempt == max_retries:
                    logger.error("OCR failed after %d retries: %s", max_retries, exc)
                    raise
                wait = backoff * (2 ** attempt)
                logger.warning("OCR attempt %d failed, retrying in %.1fs", attempt + 1, wait)
                time.sleep(wait)

    return []
