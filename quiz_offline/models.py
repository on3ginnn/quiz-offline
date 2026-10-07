"""Dataclasses для пакета комнаты и попытки."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnswerOption:
    id: int
    text: str
    is_correct: bool


@dataclass
class Question:
    id: int
    text: str
    question_type: str
    options: list[AnswerOption]
    topic_order: int | None = None


@dataclass
class TopicQuota:
    topic_order: int
    topic_title: str
    question_count: int


@dataclass
class RoomPolicy:
    name: str
    public_id: str
    time_limit_mode: str
    time_limit_minutes: int | None
    attempts_unlimited: bool
    allowed_attempts: int | None
    shuffle_questions: bool
    shuffle_options: bool
    selection_mode: str
    show_results: bool
    show_answers: bool
    show_correct_answers: bool
    grade_3_min_percent: int
    grade_4_min_percent: int
    grade_5_min_percent: int
    grade_attempt_mode: str
    questions_sample_size: int | None

    def grade_thresholds(self) -> dict[str, int]:
        return {
            "grade_3_min_percent": self.grade_3_min_percent,
            "grade_4_min_percent": self.grade_4_min_percent,
            "grade_5_min_percent": self.grade_5_min_percent,
        }

    def attempts_cap(self) -> int | None:
        if self.attempts_unlimited:
            return None
        return int(self.allowed_attempts or 1)


@dataclass
class RoomPackage:
    exported_at: str
    quiz_title: str
    quiz_kind: str
    questions: list[Question] = field(default_factory=list)
    topics: dict[int, list[Question]] = field(default_factory=dict)
    room: RoomPolicy | None = None
    topic_quotas: list[TopicQuota] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AttemptLayoutItem:
    question: Question
    topic_order: int | None
    option_ids_order: list[int]


@dataclass
class AttemptResult:
    total_questions: int
    score: int
    weighted_sum: float
    weighted_percent: int
    grade: int
    duration_sec: int
    answers: dict[int, list[int]]
