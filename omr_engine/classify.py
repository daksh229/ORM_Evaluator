"""Horizontal-line detection, two-threshold classification, and erasure detection.

This is the heart of what makes this engine different from a generic
bubble-sheet tool. We are not measuring fill ratio over the whole box — that
would mistake any stray smudge for a deliberate answer. Instead we apply a
horizontal morphological opening so that *only* horizontal-ish strokes
survive, then measure the surviving pixel ratio.
"""

import os

import cv2
import numpy as np

# Tunable thresholds (Section J4 — overridable via environment variables).
# Score is "longest horizontal run / inner-box width", so the thresholds map
# to "what fraction of the box does the horizontal line span":
#   marked   = a clear horizontal line covering at least half the box width
#   ambiguous = a partial / short / faint stretch
#   blank    = no meaningful horizontal stretch at all
MARKED_THRESHOLD = float(os.environ.get("OMR_MARKED_THRESHOLD", "0.50"))
BLANK_THRESHOLD = float(os.environ.get("OMR_BLANK_THRESHOLD", "0.10"))


def horizontal_line_score(box_crop_gray: np.ndarray) -> float:
    """Return a 0..1 score for the longest horizontal stroke in the box.

    Pipeline:
      1. Adaptive threshold to binary.
      2. Trim 20% top/bottom + 5% left/right. The vertical trim is the
         critical part — the printed box outline is itself a horizontal
         line at the very top and bottom, and after PDF.js rendering /
         perspective warp it can be 2-4 px thick. A 1-px trim was leaving
         enough outline to falsely score every box.
      3. Horizontal MORPH_OPEN with a kernel ≈ 20% of the inner width.
         Erases dots, vertical strokes, smudges, and stretches shorter
         than ~20% of the box width.
      4. Count nonzero pixels per row, take the max, and normalise by
         the inner width. This measures "longest horizontal stretch as a
         fraction of box width" — independent of box height and line
         thickness, so a 1-px pencil mark and a 5-px marker stroke
         spanning the full box both score ~1.0.
    """
    if box_crop_gray.size == 0:
        return 0.0

    h, w = box_crop_gray.shape[:2]
    if h < 8 or w < 16:
        return 0.0

    binary = cv2.adaptiveThreshold(
        box_crop_gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=11,
        C=5,
    )

    trim_y = max(3, int(h * 0.20))
    trim_x = max(2, int(w * 0.05))
    inner = binary[trim_y : h - trim_y, trim_x : w - trim_x]
    if inner.size == 0 or inner.shape[1] == 0:
        return 0.0

    kernel_w = max(3, int(inner.shape[1] * 0.2))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    horizontal = cv2.morphologyEx(inner, cv2.MORPH_OPEN, kernel)

    row_counts = np.count_nonzero(horizontal, axis=1)
    if row_counts.size == 0:
        return 0.0
    return min(1.0, float(row_counts.max()) / float(inner.shape[1]))


def classify_score(score: float) -> str:
    """Apply the two-threshold rule. Anything in between is escalated."""
    if score >= MARKED_THRESHOLD:
        return "marked"
    if score <= BLANK_THRESHOLD:
        return "blank"
    return "ambiguous"


def has_erasure_residue(box_crop_gray: np.ndarray) -> bool:
    """Heuristic erasure detector (Section J3).

    Pencil erasure typically leaves mid-grey smudge across part of the box,
    without leaving a strong dark stroke. We look for meaningful mid-tone
    coverage AND a near-absence of dark ink. The mid-tone mask is eroded
    with a 3x3 kernel so single noise pixels (JPEG / scanner grain) don't
    trigger false positives.
    """
    if box_crop_gray.size == 0:
        return False

    smudge_mask = (
        (box_crop_gray > 100) & (box_crop_gray < 200)
    ).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    eroded = cv2.erode(smudge_mask, kernel, iterations=1)

    smudge_ratio = float(np.count_nonzero(eroded)) / float(box_crop_gray.size)
    dark_ratio = float(np.count_nonzero(box_crop_gray < 80)) / float(
        box_crop_gray.size
    )

    return smudge_ratio > 0.10 and dark_ratio < 0.03


def classify_with_erasure_check(
    box_crop_gray: np.ndarray, score: float
) -> tuple[str, str | None]:
    """Two-threshold classification with an erasure-residue safety net.

    A box that the score classifies as 'blank' but where erasure residue is
    detected gets upgraded to 'ambiguous' so a human (or Claude) can review
    it — protects against the case where a student erased an answer cleanly
    enough that the dark-pixel score is low but residue remains.
    """
    base = classify_score(score)
    if base == "blank" and has_erasure_residue(box_crop_gray):
        return "ambiguous", "Possible erasure residue"
    return base, None
