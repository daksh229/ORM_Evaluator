"""Template JSON loading and box cropping."""

import json
from pathlib import Path

import numpy as np

from .models import Box, Template

TEMPLATE_DIR = Path(__file__).parent / "templates"


def load_template(template_id: str) -> Template:
    path = TEMPLATE_DIR / f"{template_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {template_id}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return Template.model_validate(data)


def list_templates() -> list[str]:
    if not TEMPLATE_DIR.exists():
        return []
    return sorted(p.stem for p in TEMPLATE_DIR.glob("*.json"))


def crop_region(
    aligned: np.ndarray,
    x_mm: float,
    y_mm: float,
    w_mm: float,
    h_mm: float,
    dpi: int = 300,
) -> np.ndarray:
    """Crop an arbitrary mm-coordinate region out of the aligned image."""
    px_per_mm = dpi / 25.4
    x = int(round(x_mm * px_per_mm))
    y = int(round(y_mm * px_per_mm))
    w = int(round(w_mm * px_per_mm))
    h = int(round(h_mm * px_per_mm))
    return aligned[y : y + h, x : x + w]


def crop_box(aligned: np.ndarray, box: Box, dpi: int = 300) -> np.ndarray:
    """Crop a single answer box out of the aligned (canonical) image."""
    return crop_region(aligned, box.x_mm, box.y_mm, box.w_mm, box.h_mm, dpi=dpi)
