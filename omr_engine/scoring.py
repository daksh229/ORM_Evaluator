"""Score per-box CV results against an answer key."""

import json
from pathlib import Path

from .models import AnswerKey, BoxResult, ScoredQuestion, ScoreReport

KEYS_DIR = Path(__file__).parent / "answer_keys"


def load_answer_key(key_id: str) -> AnswerKey:
    path = KEYS_DIR / f"{key_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Answer key not found: {key_id}")
    with path.open("r", encoding="utf-8") as f:
        return AnswerKey.model_validate(json.load(f))


def list_answer_keys() -> list[str]:
    if not KEYS_DIR.exists():
        return []
    return sorted(p.stem for p in KEYS_DIR.glob("*.json"))


def score_result(
    box_results: list[BoxResult],
    answer_key: AnswerKey,
    multi_mark_qids: list[int] | None = None,
) -> ScoreReport:
    """Score per-box CV results against an answer key.

    Single-mark questions are all-or-nothing. Multi-mark questions get
    partial credit on a per-option basis::

        score = max(0, correct - extra) / expected_count * points

    A question is treated as multi-mark if its template lists it in
    ``multi_mark_question_ids`` OR its answer-key entry expects more than
    one option.
    """
    multi_mark = set(multi_mark_qids or [])

    by_qid: dict[int, list[BoxResult]] = {}
    for br in box_results:
        by_qid.setdefault(br.question_id, []).append(br)

    scored: list[ScoredQuestion] = []
    total_earned = 0.0
    total_possible = 0.0
    correct_count = 0
    wrong_count = 0
    partial_count = 0
    wrong_qids: list[int] = []
    ambiguous_qids: list[int] = []

    for expected in answer_key.answers:
        boxes = by_qid.get(expected.question_id, [])
        selected = [b.option for b in boxes if b.status == "marked"]
        has_amb = any(b.status == "ambiguous" for b in boxes)

        expected_set = set(expected.options)
        selected_set = set(selected)

        is_multi = (
            expected.question_id in multi_mark or len(expected.options) > 1
        )

        if is_multi:
            correct_marks = len(expected_set & selected_set)
            extra_marks = len(selected_set - expected_set)
            net = max(0, correct_marks - extra_marks)
            points_earned = (
                (net / len(expected.options)) * expected.points
                if expected.options
                else 0.0
            )
            is_correct = selected_set == expected_set
            is_partial = (not is_correct) and (correct_marks > 0)
        else:
            is_correct = selected_set == expected_set
            is_partial = False
            points_earned = expected.points if is_correct else 0.0

        if is_correct:
            correct_count += 1
        elif is_partial:
            partial_count += 1
            wrong_qids.append(expected.question_id)
        else:
            wrong_count += 1
            wrong_qids.append(expected.question_id)

        if has_amb:
            ambiguous_qids.append(expected.question_id)

        total_earned += points_earned
        total_possible += expected.points

        scored.append(
            ScoredQuestion(
                question_id=expected.question_id,
                expected=sorted(expected.options),
                selected=sorted(selected),
                is_correct=is_correct,
                is_partial=is_partial,
                points_earned=round(points_earned, 2),
                points_possible=expected.points,
                has_ambiguous=has_amb,
            )
        )

    pct = (
        (total_earned / total_possible * 100) if total_possible > 0 else 0.0
    )

    return ScoreReport(
        total_points=round(total_earned, 2),
        points_possible=round(total_possible, 2),
        percentage=round(pct, 2),
        correct_count=correct_count,
        wrong_count=wrong_count,
        partial_count=partial_count,
        wrong_question_ids=sorted(set(wrong_qids)),
        ambiguous_question_ids=sorted(set(ambiguous_qids)),
        questions=scored,
    )
