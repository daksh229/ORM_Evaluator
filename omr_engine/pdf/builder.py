"""ReportLab-based answer-sheet builder.

The builder draws the printable PDF AND simultaneously records every box's
millimetre coordinates into a JSON sidecar that the OMR engine consumes. This
guarantees the printed page and the engine's geometry can never drift apart —
they are produced by the same code path in lock-step.
"""

import json
from pathlib import Path
from typing import Optional

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# --- Page geometry ---
PAGE_W_MM = 210.0
PAGE_H_MM = 297.0

# --- Fiducial markers (corner squares used for perspective alignment) ---
FIDUCIAL_SIZE_MM = 6.0
FIDUCIAL_INSET_MM = 10.0  # distance from page edge to outer edge of fiducial

# --- Answer-box geometry ---
BOX_W_MM = 8.0
BOX_H_MM = 5.0
BOX_GAP_MM = 2.0  # horizontal gap between adjacent option boxes
ROW_PITCH_MM = 9.0  # vertical centre-to-centre distance between question rows


class TemplateBuilder:
    def __init__(self, template_id: str, name: str) -> None:
        self.id = template_id
        self.name = name
        self.boxes: list[dict] = []
        self.id_boxes: list[dict] = []
        self.id_digits = 0
        self.multi_mark_qids: list[int] = []
        self._fiducials_mm: list[tuple[float, float]] = []
        self._canvas: Optional[canvas.Canvas] = None

    @property
    def c(self) -> canvas.Canvas:
        assert self._canvas is not None, "TemplateBuilder.begin() not called"
        return self._canvas

    # --- Coordinate helpers (top-down mm → bottom-up points) ---

    def _rect(
        self,
        x_mm: float,
        y_mm: float,
        w_mm: float,
        h_mm: float,
        fill: int = 0,
        stroke: int = 1,
    ) -> None:
        self.c.rect(
            x_mm * mm,
            (PAGE_H_MM - y_mm - h_mm) * mm,
            w_mm * mm,
            h_mm * mm,
            fill=fill,
            stroke=stroke,
        )

    def _line(self, x1_mm: float, y1_mm: float, x2_mm: float, y2_mm: float) -> None:
        self.c.line(
            x1_mm * mm,
            (PAGE_H_MM - y1_mm) * mm,
            x2_mm * mm,
            (PAGE_H_MM - y2_mm) * mm,
        )

    def _text(
        self,
        x_mm: float,
        y_mm: float,
        text: str,
        size: float = 10,
        anchor: str = "left",
        bold: bool = False,
    ) -> None:
        font = "Helvetica-Bold" if bold else "Helvetica"
        self.c.setFont(font, size)
        x = x_mm * mm
        y = (PAGE_H_MM - y_mm) * mm
        if anchor == "center":
            self.c.drawCentredString(x, y, text)
        elif anchor == "right":
            self.c.drawRightString(x, y, text)
        else:
            self.c.drawString(x, y, text)

    # --- Lifecycle ---

    def begin(self, pdf_path: Path) -> None:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        self._canvas = canvas.Canvas(str(pdf_path), pagesize=A4)
        self._canvas.setTitle(self.name)
        self._canvas.setAuthor("OMR Engine")
        self._canvas.setStrokeColorRGB(0, 0, 0)
        self._canvas.setFillColorRGB(0, 0, 0)
        self._canvas.setLineWidth(0.5)

    def save(self, pdf_path: Path, json_path: Path) -> None:
        self.c.showPage()
        self.c.save()

        sidecar: dict = {
            "id": self.id,
            "name": self.name,
            "page_width_mm": PAGE_W_MM,
            "page_height_mm": PAGE_H_MM,
            "fiducials_mm": [list(p) for p in self._fiducials_mm],
            "boxes": self.boxes,
        }
        if self.id_boxes:
            sidecar["student_id"] = {
                "digits": self.id_digits,
                "boxes": self.id_boxes,
            }
        if self.multi_mark_qids:
            sidecar["multi_mark_question_ids"] = sorted(self.multi_mark_qids)

        json_path.parent.mkdir(parents=True, exist_ok=True)
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(sidecar, f, indent=2)

    # --- Drawing primitives ---

    def draw_fiducials(self) -> None:
        """Draw 4 black corner squares and store their centres for the JSON.

        Order is TL, TR, BR, BL — the same order ``fiducials.detect_fiducials``
        returns and ``Template.fiducials_mm`` is required to use.
        """
        s = FIDUCIAL_SIZE_MM
        i = FIDUCIAL_INSET_MM
        squares = [
            (i, i),  # TL
            (PAGE_W_MM - i - s, i),  # TR
            (PAGE_W_MM - i - s, PAGE_H_MM - i - s),  # BR
            (i, PAGE_H_MM - i - s),  # BL
        ]
        for tlx, tly in squares:
            self._rect(tlx, tly, s, s, fill=1, stroke=0)
            self._fiducials_mm.append((tlx + s / 2, tly + s / 2))

    def draw_header(self, title: str, subtitle: str = "") -> None:
        self._text(PAGE_W_MM / 2, 22, title, size=14, anchor="center", bold=True)
        if subtitle:
            self._text(PAGE_W_MM / 2, 28, subtitle, size=9, anchor="center")
        self._text(
            PAGE_W_MM / 2,
            33,
            "Mark each answer with a single thin horizontal line in the chosen box",
            size=7,
            anchor="center",
        )
        self._line(20, 36, PAGE_W_MM - 20, 36)

    def draw_qr(self, x_mm: float, y_mm: float, size_mm: float = 16) -> None:
        """Draw a QR code containing the template ID, with a printed label."""
        qr = QrCodeWidget(self.id)
        bounds = qr.getBounds()
        qw = bounds[2] - bounds[0]
        qh = bounds[3] - bounds[1]
        size_pts = size_mm * mm
        d = Drawing(
            size_pts,
            size_pts,
            transform=[size_pts / qw, 0, 0, size_pts / qh, 0, 0],
        )
        d.add(qr)
        renderPDF.draw(
            d,
            self.c,
            x_mm * mm,
            (PAGE_H_MM - y_mm - size_mm) * mm,
        )
        self._text(
            x_mm + size_mm / 2,
            y_mm + size_mm + 3,
            self.id,
            size=6,
            anchor="center",
        )

    def draw_option_headers(
        self, x_mm: float, y_mm: float, options: list[str]
    ) -> None:
        for i, opt in enumerate(options):
            cx = x_mm + i * (BOX_W_MM + BOX_GAP_MM) + BOX_W_MM / 2
            self._text(cx, y_mm, opt, size=7, anchor="center", bold=True)

    def draw_question_row(
        self,
        qid: int,
        x_mm: float,
        y_mm: float,
        options: list[str],
        multi_mark: bool = False,
    ) -> None:
        # Question number, right-aligned just left of the first box.
        self._text(
            x_mm - 2,
            y_mm + BOX_H_MM - 1,
            str(qid),
            size=8,
            anchor="right",
            bold=True,
        )
        if multi_mark:
            tail_x = x_mm + len(options) * (BOX_W_MM + BOX_GAP_MM) + 1
            self._text(tail_x, y_mm + BOX_H_MM - 1, "[2]", size=6)
            if qid not in self.multi_mark_qids:
                self.multi_mark_qids.append(qid)

        cx = x_mm
        for opt in options:
            self._rect(cx, y_mm, BOX_W_MM, BOX_H_MM, fill=0, stroke=1)
            self.boxes.append(
                {
                    "question_id": qid,
                    "option": opt,
                    "x_mm": round(cx, 2),
                    "y_mm": round(y_mm, 2),
                    "w_mm": BOX_W_MM,
                    "h_mm": BOX_H_MM,
                }
            )
            cx += BOX_W_MM + BOX_GAP_MM

    def draw_section_header(self, title: str, x_mm: float, y_mm: float) -> None:
        self._text(x_mm, y_mm, title, size=9, bold=True)

    def draw_student_id_grid(
        self, x_mm: float, y_mm: float, digits: int = 6
    ) -> None:
        """Draw a ``digits``-column × 10-row bubble grid for the student ID.

        Each column is a digit position (left-to-right). Each row is a digit
        value 0..9. Students mark exactly one row per column with a horizontal
        line, the same way they answer questions, so the same detector reads
        both. The result is decoded by ``omr_engine.student_id.read_student_id``.
        """
        self.id_digits = digits
        self._text(x_mm, y_mm - 4, "STUDENT ID", size=8, bold=True)

        # Column headers (D1, D2, ...)
        for d in range(digits):
            cx = x_mm + d * (BOX_W_MM + BOX_GAP_MM) + BOX_W_MM / 2
            self._text(cx, y_mm - 1, f"D{d + 1}", size=6, anchor="center")

        row_pitch = BOX_H_MM + 1.0
        for row in range(10):
            row_y = y_mm + row * row_pitch
            # Row label (the digit value)
            self._text(
                x_mm - 2,
                row_y + BOX_H_MM - 1,
                str(row),
                size=7,
                anchor="right",
                bold=True,
            )
            for d in range(digits):
                bx = x_mm + d * (BOX_W_MM + BOX_GAP_MM)
                self._rect(bx, row_y, BOX_W_MM, BOX_H_MM, fill=0, stroke=1)
                self.id_boxes.append(
                    {
                        "digit_position": d,
                        "digit_value": row,
                        "x_mm": round(bx, 2),
                        "y_mm": round(row_y, 2),
                        "w_mm": BOX_W_MM,
                        "h_mm": BOX_H_MM,
                    }
                )

    def draw_footer(self) -> None:
        self._text(
            PAGE_W_MM / 2,
            PAGE_H_MM - 6,
            f"Template {self.id} — Do not fold or smudge this sheet",
            size=6,
            anchor="center",
        )
