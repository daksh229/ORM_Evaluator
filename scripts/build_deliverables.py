"""Bundle the printable PDF templates and synthetic samples into a single
``deliverables/`` directory ready to hand off.

This is a thin orchestration script — it does not regenerate anything. Run
the upstream commands first if their outputs are stale::

    python -m omr_engine.pdf.generate   # produces the PDF templates
    python -m samples.generate          # produces the synthetic test scans
    python -m scripts.build_deliverables

Output layout::

    deliverables/
    ├── DEMO_SCRIPT.md
    ├── templates/
    │   ├── AE_STANDARD.pdf
    │   ├── ADN_STANDARD.pdf
    │   ├── MULTI_SECTION.pdf
    │   └── AE_TWOMARK.pdf
    └── samples/
        ├── scans/
        └── ground_truth/
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENGINE_TEMPLATES = PROJECT_ROOT / "omr_engine" / "templates"
SAMPLES_SOURCE = PROJECT_ROOT / "samples"
DELIVERABLES_DIR = PROJECT_ROOT / "deliverables"


def copy_pdfs() -> int:
    out = DELIVERABLES_DIR / "templates"
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for pdf in sorted(ENGINE_TEMPLATES.glob("*.pdf")):
        shutil.copy2(pdf, out / pdf.name)
        count += 1
    if count == 0:
        print("  ! No PDFs found in", ENGINE_TEMPLATES)
        print("    Run `python -m omr_engine.pdf.generate` first.")
    else:
        print(f"  copied {count} PDF template(s) → {out}")
    return count


def copy_samples() -> int:
    src_scans = SAMPLES_SOURCE / "scans"
    src_gt = SAMPLES_SOURCE / "ground_truth"
    if not src_scans.exists():
        print("  ! No samples found in", src_scans)
        print("    Run `python -m samples.generate` first.")
        return 0

    out = DELIVERABLES_DIR / "samples"
    if (out / "scans").exists():
        shutil.rmtree(out / "scans")
    if (out / "ground_truth").exists():
        shutil.rmtree(out / "ground_truth")

    shutil.copytree(src_scans, out / "scans")
    count = len(list((out / "scans").glob("*.png")))
    if src_gt.exists():
        shutil.copytree(src_gt, out / "ground_truth")
    print(f"  copied {count} sample scan(s) → {out}")
    return count


def main() -> None:
    DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Building deliverables in {DELIVERABLES_DIR}\n")
    pdf_count = copy_pdfs()
    sample_count = copy_samples()
    print()
    print(f"Done — {pdf_count} template(s), {sample_count} sample(s).")
    print(f"Hand off the entire {DELIVERABLES_DIR.name}/ directory.")


if __name__ == "__main__":
    main()
