"""CSV and XLSX exports for a session's sheets."""

import csv
import io

from openpyxl import Workbook
from openpyxl.styles import Font

from .models import SheetResult

HEADERS = [
    "Sheet ID",
    "Student ID",
    "Student Name",
    "Score",
    "Max",
    "Percentage",
    "Correct",
    "Wrong",
    "Partial",
    "Ambiguous Marks",
    "Wrong Questions",
    "Ambiguous Questions",
    "Answers",
    "Timestamp",
]


def _answers_string(sheet: SheetResult) -> str:
    """Build a compact ``Q1=A;Q2=B,C`` representation."""
    by_q: dict[int, list[str]] = {}
    for br in sheet.process_result.boxes:
        if br.status == "marked":
            by_q.setdefault(br.question_id, []).append(br.option)
    return ";".join(
        f"Q{qid}={','.join(sorted(opts))}"
        for qid, opts in sorted(by_q.items())
    )


def _row(sheet: SheetResult) -> list:
    s = sheet.score
    return [
        sheet.sheet_id,
        sheet.student_id or "",
        sheet.student_name or "",
        s.total_points if s else "",
        s.points_possible if s else "",
        s.percentage if s else "",
        s.correct_count if s else "",
        s.wrong_count if s else "",
        s.partial_count if s else "",
        len(s.ambiguous_question_ids) if s else "",
        ", ".join(map(str, s.wrong_question_ids)) if s else "",
        ", ".join(map(str, s.ambiguous_question_ids)) if s else "",
        _answers_string(sheet),
        sheet.created_at,
    ]


def export_csv(sheets: list[SheetResult]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(HEADERS)
    for sheet in sheets:
        writer.writerow(_row(sheet))
    return out.getvalue()


def export_xlsx(sheets: list[SheetResult]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Results"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for sheet in sheets:
        ws.append(_row(sheet))

    # Best-effort column widths.
    for col in ws.columns:
        max_len = max(
            (len(str(cell.value)) for cell in col if cell.value is not None),
            default=10,
        )
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
