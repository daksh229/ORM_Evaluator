"""Detect the four corner fiducial markers printed on every template."""

import cv2
import numpy as np


def detect_fiducials(binary: np.ndarray) -> np.ndarray:
    """Locate the 4 printed corner squares in a binarised image.

    Returns a 4x2 ``float32`` array of pixel centres ordered TL, TR, BR, BL —
    matching the order ``Template.fiducials_mm`` is required to use.
    """
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    h, w = binary.shape
    img_area = float(h * w)

    candidates: list[tuple[float, float, float]] = []
    for c in contours:
        area = cv2.contourArea(c)
        # Fiducials are visible but small relative to the page.
        if area < img_area * 0.0001 or area > img_area * 0.01:
            continue

        x, y, bw, bh = cv2.boundingRect(c)
        if bh == 0:
            continue
        aspect = bw / bh
        if aspect < 0.7 or aspect > 1.4:
            continue

        # A solid square has high solidity; rules out broken text fragments.
        hull = cv2.convexHull(c)
        hull_area = cv2.contourArea(hull)
        if hull_area == 0:
            continue
        if area / hull_area < 0.85:
            continue

        candidates.append((x + bw / 2.0, y + bh / 2.0, area))

    if len(candidates) < 4:
        raise ValueError(
            f"Found only {len(candidates)} fiducial candidates, need 4. "
            "Check scan quality and that the template's corner markers are "
            "fully visible."
        )

    # Pick the candidate closest to each image corner. This is robust to extra
    # square-ish contours elsewhere on the page (e.g. answer boxes themselves).
    image_corners = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]
    chosen: list[tuple[float, float]] = []
    used: set[int] = set()
    for cx_img, cy_img in image_corners:
        best_idx = -1
        best_dist = float("inf")
        for i, (cx, cy, _) in enumerate(candidates):
            if i in used:
                continue
            d = (cx - cx_img) ** 2 + (cy - cy_img) ** 2
            if d < best_dist:
                best_dist = d
                best_idx = i
        used.add(best_idx)
        chosen.append((candidates[best_idx][0], candidates[best_idx][1]))

    return np.array(chosen, dtype=np.float32)
