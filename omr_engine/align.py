"""Perspective-correct a scanned page to a canonical millimetre grid."""

import cv2
import numpy as np

from .models import Template


def align_to_template(
    image: np.ndarray,
    fiducials_img: np.ndarray,
    template: Template,
    dpi: int = 300,
) -> np.ndarray:
    """Warp ``image`` so the template's mm coordinates map to pixel coordinates.

    After this call, a box at ``(x_mm, y_mm)`` in the template lives at
    ``(x_mm * dpi / 25.4, y_mm * dpi / 25.4)`` in the returned image.
    """
    px_per_mm = dpi / 25.4
    out_w = int(round(template.page_width_mm * px_per_mm))
    out_h = int(round(template.page_height_mm * px_per_mm))

    fiducials_dst = np.array(
        [(fx * px_per_mm, fy * px_per_mm) for fx, fy in template.fiducials_mm],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(fiducials_img, fiducials_dst)
    warped = cv2.warpPerspective(image, M, (out_w, out_h), borderValue=255)
    return warped
