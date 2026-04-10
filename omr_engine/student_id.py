"""Read the printed student-ID bubble grid from an aligned scan.

The grid is a 10-row × N-digit matrix of small rectangular boxes — identical
to answer boxes — so we reuse the horizontal-line detector. For each digit
position, the row whose box contains a clear horizontal line is the chosen
digit. Positions with no mark or with multiple competing marks return '?'
and a warning.
"""

import numpy as np

from .classify import MARKED_THRESHOLD, horizontal_line_score
from .models import StudentIdBlock
from .template import crop_region


def read_student_id(
    aligned: np.ndarray, block: StudentIdBlock, dpi: int = 300
) -> tuple[str, list[str]]:
    """Decode the student-ID grid. Returns ``(id_string, warnings)``."""
    by_position: dict[int, list[int]] = {}

    for box in block.boxes:
        crop = crop_region(
            aligned, box.x_mm, box.y_mm, box.w_mm, box.h_mm, dpi=dpi
        )
        score = horizontal_line_score(crop)
        if score >= MARKED_THRESHOLD:
            by_position.setdefault(box.digit_position, []).append(box.digit_value)

    chars: list[str] = []
    warnings: list[str] = []
    for pos in range(block.digits):
        marks = by_position.get(pos, [])
        if len(marks) == 1:
            chars.append(str(marks[0]))
        elif len(marks) == 0:
            chars.append("?")
            warnings.append(f"Student ID digit {pos + 1} has no mark")
        else:
            chars.append("?")
            warnings.append(
                f"Student ID digit {pos + 1} has {len(marks)} competing marks: "
                f"{sorted(marks)}"
            )

    return "".join(chars), warnings
