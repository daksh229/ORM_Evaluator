from typing import Literal

from pydantic import BaseModel, Field


class Box(BaseModel):
    """A single answer box on the printed sheet, in millimetre coordinates."""

    question_id: int
    option: str
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float


class IdBox(BaseModel):
    """A single bubble in the student-ID grid."""

    digit_position: int
    digit_value: int
    x_mm: float
    y_mm: float
    w_mm: float
    h_mm: float


class StudentIdBlock(BaseModel):
    digits: int
    boxes: list[IdBox]


class Template(BaseModel):
    """A printable answer-sheet template definition.

    Coordinates are in millimetres, measured from the top-left of the page.
    ``fiducials_mm`` MUST be ordered TL, TR, BR, BL — matching the order
    returned by ``fiducials.detect_fiducials``.
    """

    id: str
    name: str
    page_width_mm: float = 210.0
    page_height_mm: float = 297.0
    fiducials_mm: list[tuple[float, float]] = Field(min_length=4, max_length=4)
    boxes: list[Box]
    student_id: StudentIdBlock | None = None
    multi_mark_question_ids: list[int] = Field(default_factory=list)


class BoxResult(BaseModel):
    question_id: int
    option: str
    status: Literal["marked", "blank", "ambiguous"]
    score: float
    source: Literal["cv", "claude", "manual"]
    reason: str | None = None
    # Base64 PNG crop, set for boxes that hit the ambiguous band so the
    # Review Queue can show the operator the actual mark.
    image_b64: str | None = None


class ProcessResult(BaseModel):
    template_id: str
    student_id: str | None = None
    boxes: list[BoxResult]
    warnings: list[str]


# --- Answer keys + scoring (Section F) ---


class CorrectAnswer(BaseModel):
    """Expected answer for a single question.

    Single-mark questions have ``options`` of length 1. Multi-mark questions
    list every option that should be marked.
    """

    question_id: int
    options: list[str]
    points: float = 1.0


class AnswerKey(BaseModel):
    id: str
    name: str
    template_id: str
    answers: list[CorrectAnswer]


class ScoredQuestion(BaseModel):
    question_id: int
    expected: list[str]
    selected: list[str]
    is_correct: bool
    is_partial: bool  # multi-mark only: some but not all expected marks present
    points_earned: float
    points_possible: float
    has_ambiguous: bool  # at least one box for this question is ambiguous


class ScoreReport(BaseModel):
    total_points: float
    points_possible: float
    percentage: float
    correct_count: int
    wrong_count: int  # fully wrong (excludes partial)
    partial_count: int
    wrong_question_ids: list[int]  # union of wrong + partial
    ambiguous_question_ids: list[int]
    questions: list[ScoredQuestion]


# --- Sessions (Section H) ---


class SessionMeta(BaseModel):
    id: str
    name: str
    template_id: str
    answer_key_id: str | None = None
    created_at: str
    sheet_count: int = 0


class SheetResult(BaseModel):
    """A single processed sheet within a session."""

    sheet_id: str
    session_id: str
    student_id: str | None = None
    student_name: str | None = None
    process_result: ProcessResult
    score: ScoreReport | None = None
    created_at: str
