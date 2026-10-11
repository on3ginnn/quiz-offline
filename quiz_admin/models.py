"""Модели конструктора: тест, темы, вопросы и сценарий прохождения."""

from __future__ import annotations

from dataclasses import dataclass, field

QUIZ_SINGLE = "single"
QUIZ_COMPOSITE = "composite"
QUESTION_SINGLE = "single"
QUESTION_MULTIPLE = "multiple"


@dataclass
class OptionDraft:
    text: str
    is_correct: bool = False


@dataclass
class QuestionDraft:
    text: str = ""
    question_type: str = QUESTION_SINGLE
    options: list[OptionDraft] = field(default_factory=list)
    id: int | None = None


@dataclass
class Quiz:
    id: int
    title: str
    kind: str
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Topic:
    id: int
    quiz_id: int
    topic_order: int
    title: str


@dataclass
class Scenario:
    """Как воспроизводить вопросы теста; уходит в блок room пакета."""

    id: int
    quiz_id: int
    name: str
    public_id: str
    time_limit_mode: str = "auto"
    time_limit_minutes: int | None = None
    attempts_unlimited: bool = False
    allowed_attempts: int | None = 1
    shuffle_questions: bool = True
    shuffle_options: bool = True
    selection_mode: str = "per_attempt"
    show_results: bool = True
    show_answers: bool = False
    show_correct_answers: bool = False
    grade_3_min_percent: int = 70
    grade_4_min_percent: int = 80
    grade_5_min_percent: int = 90
    grade_attempt_mode: str = "best"
    questions_sample_size: int | None = None


POLICY_FIELDS = (
    "time_limit_mode",
    "time_limit_minutes",
    "attempts_unlimited",
    "allowed_attempts",
    "shuffle_questions",
    "shuffle_options",
    "selection_mode",
    "show_results",
    "show_answers",
    "show_correct_answers",
    "grade_3_min_percent",
    "grade_4_min_percent",
    "grade_5_min_percent",
    "grade_attempt_mode",
    "questions_sample_size",
)


@dataclass
class QuizSummary:
    quiz: Quiz
    question_count: int
    topic_count: int
    scenario_count: int
