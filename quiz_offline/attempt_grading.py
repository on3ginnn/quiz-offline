"""Подсчёт результата попытки."""

from __future__ import annotations

from quiz_offline.models import AttemptLayoutItem, AttemptResult, Question
from quiz_offline import scoring


def _options_by_id(question: Question) -> dict[int, object]:
    return {o.id: o for o in question.options}


def grade_attempt(
    layout: list[AttemptLayoutItem],
    answers: dict[int, list[int]],
    *,
    thresholds: dict[str, int],
    duration_sec: int,
) -> AttemptResult:
    weighted_sum = 0.0
    score = 0
    for item in layout:
        q = item.question
        selected_ids = set(answers.get(q.id, []))
        opts_by_id = _options_by_id(q)
        selected_options = [
            opts_by_id[oid] for oid in selected_ids if oid in opts_by_id
        ]
        correct_ids = {o.id for o in q.options if o.is_correct}
        wrong_ids = {o.id for o in q.options if not o.is_correct}
        weight = scoring.question_weight(
            q.question_type,
            selected_options,
            correct_ids,
            wrong_option_ids=wrong_ids,
        )
        weighted_sum += weight
        if weight >= 1.0 - 1e-9 and q.question_type == "single":
            score += 1
        elif q.question_type == "multiple":
            if (
                selected_ids == correct_ids
                and not (selected_ids & wrong_ids)
                and correct_ids
            ):
                score += 1

    total = len(layout)
    weighted_percent = scoring.weighted_sum_to_percent(weighted_sum, total)
    grade = scoring.grade_from_weighted_percent(
        weighted_percent, thresholds=thresholds
    )
    return AttemptResult(
        total_questions=total,
        score=score,
        weighted_sum=weighted_sum,
        weighted_percent=weighted_percent,
        grade=grade,
        duration_sec=duration_sec,
        answers=answers,
    )
