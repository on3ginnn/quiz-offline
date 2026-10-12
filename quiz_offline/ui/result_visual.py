"""Палитра результата попытки по проценту баллов."""

from __future__ import annotations

from dataclasses import dataclass

OUTCOME_FAIL = "#B3261E"
OUTCOME_WARN = "#9A5200"
OUTCOME_OK = "#1E7B45"
OUTCOME_FAIL_BG = "#FCEAE8"
OUTCOME_WARN_BG = "#FFF3E0"
OUTCOME_OK_BG = "#E6F4EA"


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
