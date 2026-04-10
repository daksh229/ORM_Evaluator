"""File-based session storage.

Each session is a directory under ``data/sessions/`` with a ``meta.json``
and one ``sheets/<id>.json`` per processed sheet. Deliberately simple — no
DB, no locking. School-scale (tens of sessions, hundreds of sheets per
session) does not need anything more.
"""

import uuid
from datetime import datetime
from pathlib import Path

from .models import SessionMeta, SheetResult

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSIONS_DIR = DATA_DIR / "sessions"


def _session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def _sheets_dir(session_id: str) -> Path:
    return _session_dir(session_id) / "sheets"


def _meta_path(session_id: str) -> Path:
    return _session_dir(session_id) / "meta.json"


def create_session(
    name: str, template_id: str, answer_key_id: str | None
) -> SessionMeta:
    sid = uuid.uuid4().hex[:12]
    meta = SessionMeta(
        id=sid,
        name=name,
        template_id=template_id,
        answer_key_id=answer_key_id,
        created_at=datetime.utcnow().isoformat(),
        sheet_count=0,
    )
    _sheets_dir(sid).mkdir(parents=True, exist_ok=True)
    _meta_path(sid).write_text(meta.model_dump_json(indent=2))
    return meta


def load_session(session_id: str) -> SessionMeta:
    path = _meta_path(session_id)
    if not path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    return SessionMeta.model_validate_json(path.read_text())


def list_sessions() -> list[SessionMeta]:
    if not SESSIONS_DIR.exists():
        return []
    out: list[SessionMeta] = []
    for d in SESSIONS_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            out.append(load_session(d.name))
        except Exception:
            continue
    return sorted(out, key=lambda s: s.created_at, reverse=True)


def save_sheet(session_id: str, sheet: SheetResult) -> None:
    sheets_dir = _sheets_dir(session_id)
    sheets_dir.mkdir(parents=True, exist_ok=True)
    (sheets_dir / f"{sheet.sheet_id}.json").write_text(
        sheet.model_dump_json(indent=2)
    )

    # Refresh sheet count on the meta record.
    meta = load_session(session_id)
    meta.sheet_count = len(list(sheets_dir.glob("*.json")))
    _meta_path(session_id).write_text(meta.model_dump_json(indent=2))


def list_sheets(session_id: str) -> list[SheetResult]:
    sheets_dir = _sheets_dir(session_id)
    if not sheets_dir.exists():
        return []
    out: list[SheetResult] = []
    for p in sorted(sheets_dir.glob("*.json")):
        try:
            out.append(SheetResult.model_validate_json(p.read_text()))
        except Exception:
            continue
    return out


def load_sheet(session_id: str, sheet_id: str) -> SheetResult:
    """Load a single sheet by ID. Used by the override endpoint."""
    path = _sheets_dir(session_id) / f"{sheet_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Sheet not found: {sheet_id}")
    return SheetResult.model_validate_json(path.read_text())
