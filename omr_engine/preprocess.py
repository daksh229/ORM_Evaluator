"""Image ingest, grayscale, illumination normalisation, threshold, and deskew."""

import cv2
import numpy as np


def decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image — unsupported or corrupt format")
    return img


def to_grayscale(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image


def normalize_illumination(gray: np.ndarray) -> np.ndarray:
    """Flatten uneven scanner lighting via CLAHE (Section J1).

    Cheap document scanners produce noticeably brighter areas near the lamp
    and darker areas at the page edges. CLAHE (Contrast Limited Adaptive
    Histogram Equalization) operates in tiles so each region of the page
    gets its own local contrast boost without amplifying noise — exactly
    what we need before per-region adaptive thresholding.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Local adaptive threshold — tolerant of residual illumination drift."""
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=31,
        C=10,
    )


def _hough_deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Deskew using HoughLinesP — accurate when the page contains obvious
    horizontal lines (printed dividers, ruled answer rows, table grids).
    """
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 360,
        threshold=100,
        minLineLength=100,
        maxLineGap=10,
    )
    if lines is None or len(lines) < 5:
        return gray, 0.0

    angles: list[float] = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        # Only consider near-horizontal lines; skip verticals and diagonals.
        if -30 < angle < 30:
            angles.append(angle)

    if len(angles) < 5:
        return gray, 0.0

    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.3:
        return gray, 0.0

    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), median_angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255
    )
    return rotated, median_angle


def _minarearect_deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Fallback deskew using ``cv2.minAreaRect`` over dark pixels.

    Less accurate than Hough on line-rich pages but handles sparse images
    where Hough finds nothing useful.
    """
    coords = np.column_stack(np.where(gray < 128))
    if len(coords) < 100:
        return gray, 0.0

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return gray, 0.0

    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255
    )
    return rotated, float(angle)


def deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Coarse deskew with Hough-first / minAreaRect-fallback strategy (J2).

    The fiducial-based perspective transform later in the pipeline corrects
    any remaining rotation precisely; this step just gets the page roughly
    upright so the fiducial detector can lock onto the corner squares.
    """
    rotated, angle = _hough_deskew(gray)
    if abs(angle) >= 0.3:
        return rotated, angle
    return _minarearect_deskew(gray)
