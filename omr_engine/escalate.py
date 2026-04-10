"""Escalate ambiguous-band box crops to Claude vision for final classification.

The CV pre-filter handles ~95% of marks deterministically. Only the boxes that
fall into the uncertain band between BLANK_THRESHOLD and MARKED_THRESHOLD reach
this module — keeping per-sheet token cost predictable and bounded.
"""

import base64
import json
import os
from typing import Any

import cv2
import numpy as np

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - optional dep handled at runtime
    Anthropic = None  # type: ignore[assignment]

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an OMR expert reviewing scanned answer-sheet boxes from GL/Kent/Bucks-style 11+ exams.

Pupils mark answers by drawing a thin HORIZONTAL LINE across a small rectangular box — they do NOT shade bubbles.

For EACH image provided, in order, classify it as:
- "marked":    a clear horizontal line crosses the box.
- "blank":     the box is empty / negligible noise.
- "ambiguous": faint stroke, erasure residue, smudge, or double-marked.

Be conservative: if a human should double-check, return "ambiguous".

Respond with ONLY a JSON array (no prose, no markdown fences):
[{"status": "marked"|"blank"|"ambiguous", "confidence": <0-1>, "reason": "<short>"}, ...]
The array length MUST equal the number of images, in the same order."""


def _encode_box(box_crop: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", box_crop)
    if not ok:
        raise ValueError("Failed to PNG-encode box crop")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def _fallback(reason: str, n: int) -> list[dict[str, Any]]:
    return [
        {"status": "ambiguous", "confidence": 0.0, "reason": reason}
        for _ in range(n)
    ]


def escalate_batch(
    box_crops: list[np.ndarray], model: str = HAIKU
) -> list[dict[str, Any]]:
    """Classify a batch of ambiguous box crops with one Claude vision call."""
    if not box_crops:
        return []
    if Anthropic is None:
        return _fallback("anthropic SDK not installed", len(box_crops))

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _fallback("ANTHROPIC_API_KEY not set", len(box_crops))

    client = Anthropic(api_key=api_key)

    content: list[dict[str, Any]] = []
    for crop in box_crops:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": _encode_box(crop),
                },
            }
        )
    content.append(
        {
            "type": "text",
            "text": f"Classify these {len(box_crops)} boxes in order.",
        }
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as e:  # pragma: no cover - network/API failure path
        return _fallback(f"Claude API error: {e}", len(box_crops))

    text_chunks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    if not text_chunks:
        return _fallback("Claude returned no text", len(box_crops))

    try:
        parsed = json.loads(_strip_fences("".join(text_chunks)))
    except json.JSONDecodeError as e:
        return _fallback(f"Claude returned invalid JSON: {e}", len(box_crops))

    if not isinstance(parsed, list):
        return _fallback("Claude response was not a JSON array", len(box_crops))

    result: list[dict[str, Any]] = []
    for i in range(len(box_crops)):
        if i >= len(parsed) or not isinstance(parsed[i], dict):
            result.append(
                {
                    "status": "ambiguous",
                    "confidence": 0.0,
                    "reason": "Missing classification for this image",
                }
            )
            continue
        item = parsed[i]
        result.append(
            {
                "status": item.get("status", "ambiguous"),
                "confidence": float(item.get("confidence", 0.0)),
                "reason": item.get("reason", ""),
            }
        )
    return result
