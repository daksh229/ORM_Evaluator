"""Test harness — run the OMR engine over the synthetic samples and report accuracy.

Use this for regression testing whenever you change the pipeline. A drop in
the reported accuracy on the clean sample is a strong signal that something
in the CV pre-filter, deskew, or fiducial detection has regressed.

Run from the project root::

    python -m samples.generate     # generate the samples first (one-time)
    python -m scripts.test_harness
"""

import json
import sys
from pathlib import Path

from omr_engine.pipeline import process_scan
from omr_engine.template import load_template

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANS_DIR = PROJECT_ROOT / "samples" / "scans"
GROUND_TRUTH_DIR = PROJECT_ROOT / "samples" / "ground_truth"


def evaluate_sheet(scan_path: Path, gt_path: Path) -> dict:
    gt = json.loads(gt_path.read_text())
    template = load_template(gt["template_id"])
    expected = {
        (m["question_id"], m["option"]) for m in gt["expected_marks"]
    }

    image_bytes = scan_path.read_bytes()
    result = process_scan(image_bytes, template)

    if not result.boxes:
        return {
            "name": scan_path.name,
            "ok": False,
            "warnings": result.warnings,
            "total": 0,
            "correct": 0,
            "fp": 0,
            "fn": 0,
            "ambiguous": 0,
            "accuracy": 0.0,
        }

    total = len(result.boxes)
    correct = 0
    fp = 0
    fn = 0
    ambiguous = 0

    for box in result.boxes:
        key = (box.question_id, box.option)
        should_be_marked = key in expected
        if box.status == "ambiguous":
            ambiguous += 1
            continue
        actually_marked = box.status == "marked"
        if should_be_marked == actually_marked:
            correct += 1
        elif actually_marked:
            fp += 1
        else:
            fn += 1

    accuracy = (correct / total * 100.0) if total else 0.0
    return {
        "name": scan_path.name,
        "ok": True,
        "warnings": result.warnings,
        "total": total,
        "correct": correct,
        "fp": fp,
        "fn": fn,
        "ambiguous": ambiguous,
        "accuracy": accuracy,
    }


def main() -> int:
    if not SCANS_DIR.exists():
        print("No scans directory. Run `python -m samples.generate` first.")
        return 1

    scans = sorted(SCANS_DIR.glob("*.png"))
    if not scans:
        print("No sample scans found in", SCANS_DIR)
        return 1

    print(f"Running OMR engine over {len(scans)} sample(s)...\n")

    grand_total = 0
    grand_correct = 0
    grand_fp = 0
    grand_fn = 0
    grand_ambiguous = 0
    failures: list[str] = []

    for scan in scans:
        gt = GROUND_TRUTH_DIR / f"{scan.stem}.json"
        if not gt.exists():
            print(f"  ! {scan.name}: no ground truth at {gt.name}")
            continue

        report = evaluate_sheet(scan, gt)
        if not report["ok"]:
            print(f"  ✗ {scan.name}: pipeline failed — {report['warnings']}")
            failures.append(scan.name)
            continue

        grand_total += report["total"]
        grand_correct += report["correct"]
        grand_fp += report["fp"]
        grand_fn += report["fn"]
        grand_ambiguous += report["ambiguous"]

        marker = "✓" if report["accuracy"] >= 99.0 else ("~" if report["accuracy"] >= 90.0 else "✗")
        print(
            f"  {marker} {scan.name}: "
            f"{report['correct']}/{report['total']} ({report['accuracy']:.2f}%) "
            f"fp={report['fp']} fn={report['fn']} amb={report['ambiguous']}"
        )
        if report["warnings"]:
            for w in report["warnings"]:
                print(f"      warning: {w}")

    overall = (grand_correct / grand_total * 100.0) if grand_total else 0.0
    print()
    print("=" * 50)
    print(f"Total boxes:      {grand_total}")
    print(f"Correct:          {grand_correct}")
    print(f"False positives:  {grand_fp}")
    print(f"False negatives:  {grand_fn}")
    print(f"Ambiguous:        {grand_ambiguous}")
    print(f"Overall accuracy: {overall:.2f}%")
    print("=" * 50)

    if failures:
        print(f"\n{len(failures)} sheet(s) failed to process:")
        for name in failures:
            print(f"  - {name}")
        return 2

    return 0 if overall >= 95.0 else 1


if __name__ == "__main__":
    sys.exit(main())
