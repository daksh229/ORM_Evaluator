"""Synthesize filled test scans + ground truth for the test harness.

Drawing horizontal lines directly into the template's box coordinates produces
synthetic images that exercise the entire pipeline (deskew → fiducials →
align → classify) the same way a real scanned sheet would. The line thickness
(12 px at 300 DPI ≈ 1 mm) is tuned to score comfortably above
``MARKED_THRESHOLD=0.18`` so a clean synthetic scan should hit ~100% accuracy.

Variants generated:

- ``sample_01_clean``    — flat A-E test, no perturbation
- ``sample_02_rotated`` — same answers, rotated 2 degrees (exercises deskew)
- ``sample_03_noisy``   — same answers with gaussian sensor noise
- ``sample_04_adn``     — A/D/N template, sparse marks
- ``sample_05_twomark`` — multi-mark questions in Q21-30

Run from the project root::

    python -m samples.generate
"""

import json
from pathlib import Path

import cv2
import numpy as np

from omr_engine.template import load_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANS_DIR = PROJECT_ROOT / "samples" / "scans"
GROUND_TRUTH_DIR = PROJECT_ROOT / "samples" / "ground_truth"

DPI = 300
LINE_THICKNESS_PX = 12  # ~1 mm at 300 DPI; tuned to score above MARKED_THRESHOLD
FIDUCIAL_SIZE_MM = 6.0


def render_sample(
    template_id: str,
    sample_id: str,
    expected_marks: list[dict],
    rotation_deg: float = 0.0,
    add_noise: bool = False,
) -> None:
    template = load_template(template_id)
    px_per_mm = DPI / 25.4
    w_px = int(round(template.page_width_mm * px_per_mm))
    h_px = int(round(template.page_height_mm * px_per_mm))

    # White page
    img = np.full((h_px, w_px), 255, dtype=np.uint8)

    # Corner fiducial squares
    half_s = int(round((FIDUCIAL_SIZE_MM / 2) * px_per_mm))
    for fx_mm, fy_mm in template.fiducials_mm:
        cx = int(round(fx_mm * px_per_mm))
        cy = int(round(fy_mm * px_per_mm))
        cv2.rectangle(img, (cx - half_s, cy - half_s), (cx + half_s, cy + half_s), 0, -1)

    # Print every answer-box outline so the page looks like a real form
    # (and so Hough deskew has horizontal lines to lock onto).
    for box in template.boxes:
        x = int(round(box.x_mm * px_per_mm))
        y = int(round(box.y_mm * px_per_mm))
        w = int(round(box.w_mm * px_per_mm))
        h = int(round(box.h_mm * px_per_mm))
        cv2.rectangle(img, (x, y), (x + w, y + h), 0, 1)

    # Print the student-ID grid outlines too if the template has one.
    if template.student_id is not None:
        for ib in template.student_id.boxes:
            x = int(round(ib.x_mm * px_per_mm))
            y = int(round(ib.y_mm * px_per_mm))
            w = int(round(ib.w_mm * px_per_mm))
            h = int(round(ib.h_mm * px_per_mm))
            cv2.rectangle(img, (x, y), (x + w, y + h), 0, 1)

    # Draw a thick horizontal line in each box that should be 'marked'.
    expected_set = {(m["question_id"], m["option"]) for m in expected_marks}
    for box in template.boxes:
        if (box.question_id, box.option) not in expected_set:
            continue
        x = int(round(box.x_mm * px_per_mm))
        y = int(round(box.y_mm * px_per_mm))
        w = int(round(box.w_mm * px_per_mm))
        h = int(round(box.h_mm * px_per_mm))
        line_y = y + h // 2
        cv2.line(
            img,
            (x + 4, line_y),
            (x + w - 4, line_y),
            0,
            LINE_THICKNESS_PX,
        )

    # Optional rotation — exercises the deskew stage.
    if rotation_deg != 0.0:
        M = cv2.getRotationMatrix2D((w_px / 2, h_px / 2), rotation_deg, 1.0)
        img = cv2.warpAffine(img, M, (w_px, h_px), borderValue=255)

    # Optional gaussian noise — exercises the adaptive threshold + CLAHE path.
    if add_noise:
        rng = np.random.default_rng(seed=42)
        noise = rng.normal(0, 5, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    SCANS_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    out_img = SCANS_DIR / f"{sample_id}.png"
    out_gt = GROUND_TRUTH_DIR / f"{sample_id}.json"

    cv2.imwrite(str(out_img), img)
    out_gt.write_text(
        json.dumps(
            {
                "template_id": template_id,
                "expected_marks": expected_marks,
            },
            indent=2,
        )
    )

    print(f"  wrote {out_img.name} ({len(expected_marks)} marks)")


def main() -> None:
    options_ae = ["A", "B", "C", "D", "E"]

    # Sample 1 — clean AE_STANDARD, cycles A-E for 50 questions.
    cycle_ae = [
        {"question_id": q, "option": options_ae[(q - 1) % 5]}
        for q in range(1, 51)
    ]
    render_sample("AE_STANDARD", "sample_01_clean", cycle_ae)

    # Sample 2 — same answers, rotated 2 degrees.
    render_sample("AE_STANDARD", "sample_02_rotated", cycle_ae, rotation_deg=2.0)

    # Sample 3 — same answers with gaussian noise.
    render_sample("AE_STANDARD", "sample_03_noisy", cycle_ae, add_noise=True)

    # Sample 4 — ADN_STANDARD, sparse marks (every other question).
    cycle_adn = [
        {"question_id": q, "option": "D"} for q in range(1, 51, 2)
    ]
    render_sample("ADN_STANDARD", "sample_04_adn", cycle_adn)

    # Sample 5 — AE_TWOMARK, multi-mark on Q21-30.
    twomark_marks: list[dict] = []
    for q in range(1, 21):
        twomark_marks.append({"question_id": q, "option": "B"})
    for q in range(21, 31):
        twomark_marks.append({"question_id": q, "option": "A"})
        twomark_marks.append({"question_id": q, "option": "C"})
    render_sample("AE_TWOMARK", "sample_05_twomark", twomark_marks)

    print(f"\nSamples written to {SCANS_DIR}")
    print(f"Ground truth written to {GROUND_TRUTH_DIR}")


if __name__ == "__main__":
    main()
