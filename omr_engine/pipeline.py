"""End-to-end OMR pipeline orchestration."""

import base64

import cv2
import numpy as np

from .align import align_to_template
from .classify import classify_with_erasure_check, horizontal_line_score
from .escalate import escalate_batch
from .fiducials import detect_fiducials
from .models import BoxResult, ProcessResult, Template
from .preprocess import (
    adaptive_threshold,
    decode_image,
    deskew,
    normalize_illumination,
    to_grayscale,
)
from .student_id import read_student_id
from .template import crop_box


def _encode_png(crop: np.ndarray) -> str:
    """Base64-encode a box crop as PNG for embedding in the JSON response."""
    ok, buf = cv2.imencode(".png", crop)
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def process_scan(image_bytes: bytes, template: Template) -> ProcessResult:
    warnings: list[str] = []

    # 1. Decode + grayscale.
    image = decode_image(image_bytes)
    gray = to_grayscale(image)

    # 2. Flatten uneven scanner illumination (J1).
    gray = normalize_illumination(gray)

    # 3. Coarse rotation correction (J2).
    deskewed, angle = deskew(gray)
    if abs(angle) > 0.5:
        warnings.append(f"Deskewed by {angle:.2f} degrees")

    # 4. Binarise for fiducial detection.
    binary = adaptive_threshold(deskewed)

    # 5. Locate the 4 corner fiducials.
    try:
        fiducials_img = detect_fiducials(binary)
    except ValueError as e:
        return ProcessResult(
            template_id=template.id,
            student_id=None,
            boxes=[],
            warnings=[str(e)],
        )

    # 6. Perspective-correct to canonical mm grid.
    aligned = align_to_template(deskewed, fiducials_img, template)

    # 7. Read student ID bubble grid (if the template has one).
    student_id: str | None = None
    if template.student_id is not None:
        student_id, id_warnings = read_student_id(aligned, template.student_id)
        warnings.extend(id_warnings)

    # 8. Per-box CV classification with erasure-residue safety net (J3).
    box_results: list[BoxResult] = []
    ambiguous_records: list[tuple[int, np.ndarray]] = []

    for i, box in enumerate(template.boxes):
        crop = crop_box(aligned, box)
        score = horizontal_line_score(crop)
        status, note = classify_with_erasure_check(crop, score)
        box_results.append(
            BoxResult(
                question_id=box.question_id,
                option=box.option,
                status=status,  # type: ignore[arg-type]
                score=score,
                source="cv",
                reason=note,
            )
        )
        if status == "ambiguous":
            ambiguous_records.append((i, crop))

    # 9. Escalate the ambiguous-band boxes to Claude in one batched call.
    #    Crops for these boxes are also stored on the BoxResult so the
    #    Review Queue can render them without re-running the engine.
    if ambiguous_records:
        crops_only = [crop for _, crop in ambiguous_records]
        escalations = escalate_batch(crops_only)
        for (idx, crop), esc in zip(ambiguous_records, escalations):
            cv_note = box_results[idx].reason
            claude_note = esc.get("reason", "")
            box_results[idx].status = esc["status"]
            box_results[idx].source = "claude"
            box_results[idx].reason = (
                f"{cv_note}; {claude_note}" if cv_note else claude_note
            )
            box_results[idx].image_b64 = _encode_png(crop)

    return ProcessResult(
        template_id=template.id,
        student_id=student_id,
        boxes=box_results,
        warnings=warnings,
    )
