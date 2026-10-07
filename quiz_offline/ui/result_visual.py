"""Палитра результата попытки по проценту баллов."""

from __future__ import annotations

from dataclasses import dataclass

OUTCOME_FAIL = "#D32F2F"
OUTCOME_WARN = "#F57C00"
OUTCOME_OK = "#2E7D32"
OUTCOME_FAIL_BG = "#fdecea"
OUTCOME_WARN_BG = "#fff8e1"
OUTCOME_OK_BG = "#e8f5e9"


@dataclass(frozen=True)
class ResultOutcomeVisual:
    tone: str  # fail | warn | ok
    color: str
    bg: str


def outcome_for_percent(percent: float) -> ResultOutcomeVisual:
    p = max(0.0, min(100.0, float(percent)))
    if p < 40:
        return ResultOutcomeVisual(
            tone="fail",
            color=OUTCOME_FAIL,
            bg=OUTCOME_FAIL_BG,
        )
    if p < 70:
        return ResultOutcomeVisual(
            tone="warn",
            color=OUTCOME_WARN,
            bg=OUTCOME_WARN_BG,
        )
    return ResultOutcomeVisual(
        tone="ok",
        color=OUTCOME_OK,
        bg=OUTCOME_OK_BG,
    )


def format_grade_scale_caption(grade: int) -> str:
    """Подпись под кольцом: оценка на 5-балльной шкале без дублирования %."""
    return f"{grade} из 5"
