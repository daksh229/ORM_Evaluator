"""Build all printable answer-sheet template variants.

Run from the project root:

    python -m omr_engine.pdf.generate

Each variant produces a paired ``<ID>.pdf`` (printable) and ``<ID>.json``
(engine sidecar) inside ``omr_engine/templates/``.
"""

from pathlib import Path

from .builder import (
    BOX_H_MM,
    ROW_PITCH_MM,
    TemplateBuilder,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "templates"


def build_ae_standard() -> None:
    """50-question Standard A-E sheet, 2 columns of 25."""
    b = TemplateBuilder("AE_STANDARD", "Standard A-E Answer Sheet (50 questions)")
    b.begin(OUT_DIR / "AE_STANDARD.pdf")
    b.draw_fiducials()
    b.draw_header("Mock Exam Answer Sheet", "GL-Style A-E Standard")
    b.draw_qr(178, 42, size_mm=15)
    b.draw_student_id_grid(x_mm=140, y_mm=85, digits=6)

    options = ["A", "B", "C", "D", "E"]
    col1_x = 22
    col2_x = 78
    start_y = 50

    b.draw_option_headers(col1_x, start_y - 2, options)
    b.draw_option_headers(col2_x, start_y - 2, options)

    for i in range(25):
        y = start_y + i * ROW_PITCH_MM
        b.draw_question_row(i + 1, col1_x, y, options)
        b.draw_question_row(i + 26, col2_x, y, options)

    b.draw_footer()
    b.save(OUT_DIR / "AE_STANDARD.pdf", OUT_DIR / "AE_STANDARD.json")
    print(f"Built AE_STANDARD ({len(b.boxes)} answer boxes)")


def build_adn_standard() -> None:
    """50-question A-D-N variant (3 options per question)."""
    b = TemplateBuilder("ADN_STANDARD", "A-D-N Answer Sheet (50 questions)")
    b.begin(OUT_DIR / "ADN_STANDARD.pdf")
    b.draw_fiducials()
    b.draw_header("Mock Exam Answer Sheet", "GL-Style A / D / N Variant")
    b.draw_qr(178, 42, size_mm=15)
    b.draw_student_id_grid(x_mm=140, y_mm=85, digits=6)

    options = ["A", "D", "N"]
    col1_x = 22
    col2_x = 70
    start_y = 50

    b.draw_option_headers(col1_x, start_y - 2, options)
    b.draw_option_headers(col2_x, start_y - 2, options)

    for i in range(25):
        y = start_y + i * ROW_PITCH_MM
        b.draw_question_row(i + 1, col1_x, y, options)
        b.draw_question_row(i + 26, col2_x, y, options)

    b.draw_footer()
    b.save(OUT_DIR / "ADN_STANDARD.pdf", OUT_DIR / "ADN_STANDARD.json")
    print(f"Built ADN_STANDARD ({len(b.boxes)} answer boxes)")


def build_multi_section() -> None:
    """Three sections with different option sets on a single sheet."""
    b = TemplateBuilder(
        "MULTI_SECTION", "Multi-Section Mock (Verbal / Numerical / True-False)"
    )
    b.begin(OUT_DIR / "MULTI_SECTION.pdf")
    b.draw_fiducials()
    b.draw_header("Mock Exam Answer Sheet", "Multi-Section Layout")
    b.draw_qr(178, 42, size_mm=15)
    b.draw_student_id_grid(x_mm=140, y_mm=85, digits=6)

    # Section 1 — Verbal Reasoning, A-E, Q1-15
    sec1_x = 22
    sec1_y = 52
    b.draw_section_header("Section 1 — Verbal Reasoning (A-E)", sec1_x, sec1_y - 4)
    options_ae = ["A", "B", "C", "D", "E"]
    b.draw_option_headers(sec1_x, sec1_y - 1, options_ae)
    for i in range(15):
        b.draw_question_row(
            i + 1, sec1_x, sec1_y + i * ROW_PITCH_MM, options_ae
        )

    # Section 2 — Numerical Reasoning, A-D, Q16-30
    sec2_x = 78
    sec2_y = 52
    b.draw_section_header("Section 2 — Numerical (A-D)", sec2_x, sec2_y - 4)
    options_ad = ["A", "B", "C", "D"]
    b.draw_option_headers(sec2_x, sec2_y - 1, options_ad)
    for i in range(15):
        b.draw_question_row(
            i + 16, sec2_x, sec2_y + i * ROW_PITCH_MM, options_ad
        )

    # Section 3 — True/False, Q31-40
    sec3_x = 22
    sec3_y = 200
    b.draw_section_header("Section 3 — True / False", sec3_x, sec3_y - 4)
    options_tf = ["T", "F"]
    b.draw_option_headers(sec3_x, sec3_y - 1, options_tf)
    for i in range(10):
        b.draw_question_row(
            i + 31, sec3_x, sec3_y + i * ROW_PITCH_MM, options_tf
        )

    b.draw_footer()
    b.save(OUT_DIR / "MULTI_SECTION.pdf", OUT_DIR / "MULTI_SECTION.json")
    print(f"Built MULTI_SECTION ({len(b.boxes)} answer boxes)")


def build_ae_twomark() -> None:
    """A-E sheet where Q21-30 require TWO marks per question."""
    b = TemplateBuilder("AE_TWOMARK", "A-E with Multi-Mark Section (Q21-30)")
    b.begin(OUT_DIR / "AE_TWOMARK.pdf")
    b.draw_fiducials()
    b.draw_header("Mock Exam Answer Sheet", "A-E with Multi-Mark Section")
    b.draw_qr(178, 42, size_mm=15)
    b.draw_student_id_grid(x_mm=140, y_mm=85, digits=6)

    options = ["A", "B", "C", "D", "E"]

    # Q1-20 single mark, left column
    sec1_x = 22
    sec1_y = 52
    b.draw_section_header("Single mark per question", sec1_x, sec1_y - 4)
    b.draw_option_headers(sec1_x, sec1_y - 1, options)
    for i in range(20):
        b.draw_question_row(
            i + 1, sec1_x, sec1_y + i * ROW_PITCH_MM, options
        )

    # Q21-30 two marks, lower-right area below the ID grid
    sec2_x = 78
    sec2_y = 165
    b.draw_section_header("Mark TWO answers per question", sec2_x, sec2_y - 4)
    b.draw_option_headers(sec2_x, sec2_y - 1, options)
    for i in range(10):
        b.draw_question_row(
            i + 21, sec2_x, sec2_y + i * ROW_PITCH_MM, options, multi_mark=True
        )

    b.draw_footer()
    b.save(OUT_DIR / "AE_TWOMARK.pdf", OUT_DIR / "AE_TWOMARK.json")
    print(
        f"Built AE_TWOMARK ({len(b.boxes)} answer boxes, "
        f"{len(b.multi_mark_qids)} multi-mark questions)"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    build_ae_standard()
    build_adn_standard()
    build_multi_section()
    build_ae_twomark()
    print(f"\nAll templates written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
