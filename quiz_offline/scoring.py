"""
Взвешенная оценка (копия backend/quiz/scoring.py без Django-зависимостей).
"""
from __future__ import annotations

import decimal
from typing import Collection, Optional, Set

GRADE_5_MIN_PERCENT = decimal.Decimal("85")
GRADE_4_MIN_PERCENT = decimal.Decimal("70")
GRADE_3_MIN_PERCENT = decimal.Decimal("50")

DEFAULT_GRADE_5_MIN_PERCENT = 90
DEFAULT_GRADE_4_MIN_PERCENT = 80
DEFAULT_GRADE_3_MIN_PERCENT = 70


def multiple_linear_weight(
    selected_ids: Set[int],
    correct_ids: Set[int],
    wrong_ids: Set[int],
) -> float:
    c = len(correct_ids)
    if c == 0:
        return 0.0
    s_correct = len(selected_ids & correct_ids)
    s_wrong = len(selected_ids & wrong_ids)
    raw = (float(s_correct) - float(s_wrong)) / float(c)
    return max(0.0, min(1.0, raw))


def f1_for_option_sets(
    selected_ids: Collection[int],
    correct_ids: Collection[int],
) -> float:
    s = {int(x) for x in selected_ids}
    y = {int(x) for x in correct_ids}
    if not s or not y:
        return 0.0
    inter = len(s & y)
    if inter == 0:
        return 0.0
    p = inter / len(s)
    r = inter / len(y)
    if p + r == 0:
        return 0.0
    return 2.0 * p * r / (p + r)


def question_weight(
    question_type: str,
    selected_options,
    correct_option_ids: Set[int],
    *,
    wrong_option_ids: Optional[Set[int]] = None,
) -> float:
    options = list(selected_options) if selected_options is not None else []
    if not options:
        return 0.0
    st = (question_type or "").lower()
    if st == "single":
        return 1.0 if len(options) == 1 and bool(options[0].is_correct) else 0.0
    if st == "multiple":
        if not correct_option_ids:
            return 0.0
        wrong = wrong_option_ids if wrong_option_ids is not None else set()
        selected_ids = {int(o.id) for o in options}
        return multiple_linear_weight(selected_ids, set(correct_option_ids), wrong)
    return 0.0


def points_earned_from_option_payload(
    question_type: str,
    option_payload: list[dict],
) -> float:
    st = (question_type or "").lower()
    if st == "single":
        selected = [o for o in option_payload if o.get("selected")]
        if len(selected) != 1:
            return 0.0
        return 1.0 if selected[0].get("is_correct") else 0.0
    if st == "multiple":
        correct_ids = {
            int(o["option_id"])
            for o in option_payload
            if o.get("option_id") is not None and o.get("is_correct")
        }
        wrong_ids = {
            int(o["option_id"])
            for o in option_payload
            if o.get("option_id") is not None and not o.get("is_correct")
        }
        selected_ids = {
            int(o["option_id"])
            for o in option_payload
            if o.get("selected") and o.get("option_id") is not None
        }
        return multiple_linear_weight(selected_ids, correct_ids, wrong_ids)
    return 0.0


def weighted_sum_to_percent(weighted_sum: float, total_questions: int) -> int:
    if not total_questions or total_questions <= 0:
        return 0
    p = 100.0 * float(weighted_sum) / float(total_questions)
    return int(round(p))


def grade_from_weighted_percent(
    percent: int,
    *,
    thresholds: dict[str, int] | None = None,
) -> int:
    p = int(percent) if percent is not None else 0
    p = max(0, min(100, p))
    if thresholds:
        g5 = int(thresholds.get("grade_5_min_percent", DEFAULT_GRADE_5_MIN_PERCENT))
        g4 = int(thresholds.get("grade_4_min_percent", DEFAULT_GRADE_4_MIN_PERCENT))
        g3 = int(thresholds.get("grade_3_min_percent", DEFAULT_GRADE_3_MIN_PERCENT))
    else:
        g5 = int(GRADE_5_MIN_PERCENT)
        g4 = int(GRADE_4_MIN_PERCENT)
        g3 = int(GRADE_3_MIN_PERCENT)
    if p >= g5:
        return 5
    if p >= g4:
        return 4
    if p >= g3:
        return 3
    return 2
