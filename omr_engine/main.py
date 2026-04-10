"""FastAPI entrypoint for the OMR engine.

Run with:
    uvicorn omr_engine.main:app --host 0.0.0.0 --port 8000 --reload
"""

import uuid
from datetime import datetime

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from .exports import export_csv, export_xlsx
from .models import SheetResult
from .pipeline import process_scan
from .scoring import list_answer_keys, load_answer_key, score_result
from .sessions import (
    create_session,
    list_sessions,
    list_sheets,
    load_session,
    load_sheet,
    save_sheet,
)
from .template import list_templates, load_template

app = FastAPI(title="OMR Engine", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/templates")
def templates() -> dict[str, list[str]]:
    return {"templates": list_templates()}


@app.get("/answer-keys")
def answer_keys() -> dict[str, list[str]]:
    return {"answer_keys": list_answer_keys()}


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    answer_key_id: str | None = Form(None),
) -> dict:
    """Process a single scan WITHOUT persisting it. Used by the legacy
    /api/process-scan bridge for one-off testing. The session endpoints
    are the recommended path for batch workflows."""
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file upload")

    try:
        template = load_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Unknown template: {template_id}")

    try:
        result = process_scan(image_bytes, template)
    except ValueError as e:
        raise HTTPException(422, str(e))

    response = result.model_dump()
    if answer_key_id:
        try:
            ak = load_answer_key(answer_key_id)
            response["score"] = score_result(
                result.boxes, ak, template.multi_mark_question_ids
            ).model_dump()
        except FileNotFoundError:
            response["score"] = None
    return response


# --- Session management ---


@app.post("/sessions")
def create_session_endpoint(
    name: str = Form(...),
    template_id: str = Form(...),
    answer_key_id: str | None = Form(None),
) -> dict:
    return create_session(name, template_id, answer_key_id).model_dump()


@app.get("/sessions")
def list_sessions_endpoint() -> dict:
    return {"sessions": [s.model_dump() for s in list_sessions()]}


@app.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str) -> dict:
    try:
        meta = load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(404, "Session not found")
    sheets = list_sheets(session_id)
    return {
        "meta": meta.model_dump(),
        "sheets": [s.model_dump() for s in sheets],
    }


@app.post("/sessions/{session_id}/scans")
async def add_scan(
    session_id: str,
    file: UploadFile = File(...),
    student_name: str | None = Form(None),
) -> dict:
    try:
        meta = load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(404, "Session not found")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(400, "Empty file upload")

    try:
        template = load_template(meta.template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {meta.template_id}")

    try:
        result = process_scan(image_bytes, template)
    except ValueError as e:
        raise HTTPException(422, str(e))

    score_report = None
    if meta.answer_key_id:
        try:
            ak = load_answer_key(meta.answer_key_id)
            score_report = score_result(
                result.boxes, ak, template.multi_mark_question_ids
            )
        except FileNotFoundError:
            pass  # Session references a missing answer key — return raw result.

    sheet = SheetResult(
        sheet_id=uuid.uuid4().hex[:8],
        session_id=session_id,
        student_id=result.student_id,
        student_name=student_name,
        process_result=result,
        score=score_report,
        created_at=datetime.utcnow().isoformat(),
    )
    save_sheet(session_id, sheet)
    return sheet.model_dump()


@app.get("/sessions/{session_id}/export.csv")
def export_session_csv(session_id: str) -> Response:
    try:
        load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(404, "Session not found")
    sheets = list_sheets(session_id)
    return Response(
        content=export_csv(sheets),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}.csv"'
        },
    )


@app.get("/sessions/{session_id}/export.xlsx")
def export_session_xlsx(session_id: str) -> Response:
    try:
        load_session(session_id)
    except FileNotFoundError:
        raise HTTPException(404, "Session not found")
    sheets = list_sheets(session_id)
    return Response(
        content=export_xlsx(sheets),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{session_id}.xlsx"'
        },
    )


@app.patch("/sessions/{session_id}/sheets/{sheet_id}/boxes/{box_index}")
def override_box(
    session_id: str,
    sheet_id: str,
    box_index: int,
    status: str,
) -> dict:
    """Manually override a single box's classification (Section I2/I3).

    Used by the Review Queue when an operator overrules the AI's call. The
    sheet's score is recomputed if the session has an answer key, so CSV /
    XLSX exports immediately reflect the override.
    """
    if status not in ("marked", "blank", "ambiguous"):
        raise HTTPException(400, f"Invalid status: {status}")

    try:
        sheet = load_sheet(session_id, sheet_id)
    except FileNotFoundError:
        raise HTTPException(404, "Sheet not found")

    if box_index < 0 or box_index >= len(sheet.process_result.boxes):
        raise HTTPException(404, "Box index out of range")

    box = sheet.process_result.boxes[box_index]
    box.status = status  # type: ignore[assignment]
    box.source = "manual"
    box.reason = "Operator override"

    # Re-score against the answer key (if any) so exports reflect the override.
    try:
        meta = load_session(session_id)
        if meta.answer_key_id:
            ak = load_answer_key(meta.answer_key_id)
            template = load_template(meta.template_id)
            sheet.score = score_result(
                sheet.process_result.boxes,
                ak,
                template.multi_mark_question_ids,
            )
    except FileNotFoundError:
        pass

    save_sheet(session_id, sheet)
    return sheet.model_dump()
