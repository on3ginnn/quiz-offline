"""Правила проверки вопросов, сценариев и готового пакета (как у загрузчика плеера)."""

from __future__ import annotations

from typing import Any

from quiz_admin.models import (
    QUESTION_MULTIPLE,
    QUESTION_SINGLE,
    QUIZ_COMPOSITE,
    QUIZ_SINGLE,
    OptionDraft,
    QuestionDraft,
    Scenario,
)

MAX_OPTION_LENGTH = 500
MAX_ATTEMPTS = 10


class PackageValidationError(ValueError):
    """Набор найденных проблем; ``errors`` — человекочитаемые строки."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def validate_question(question: QuestionDraft, label: str = "Вопрос") -> list[str]:
    errors: list[str] = []
    if not (question.text or "").strip():
        errors.append(f"{label}: пустой текст вопроса.")
    if question.question_type not in (QUESTION_SINGLE, QUESTION_MULTIPLE):
        errors.append(f"{label}: неизвестный тип «{question.question_type}».")
    if len(question.options) < 2:
        errors.append(f"{label}: нужно минимум 2 варианта ответа.")
    for idx, option in enumerate(question.options, start=1):
        text = (option.text or "").strip()
        if not text:
            errors.append(f"{label}: пустой вариант №{idx}.")
        elif len(text) > MAX_OPTION_LENGTH:
            errors.append(
                f"{label}: вариант №{idx} длиннее {MAX_OPTION_LENGTH} символов."
            )
    correct = sum(1 for o in question.options if o.is_correct)
    if correct == 0:
        errors.append(f"{label}: не отмечен правильный вариант.")
    elif question.question_type == QUESTION_SINGLE and correct != 1:
        errors.append(
            f"{label}: в вопросе с одним ответом должен быть ровно один правильный."
        )
    return errors


def validate_questions(questions: list[QuestionDraft], prefix: str = "") -> list[str]:
    errors: list[str] = []
    for idx, question in enumerate(questions, start=1):
        errors.extend(validate_question(question, f"{prefix}Вопрос {idx}"))
    return errors


def validate_scenario(scenario: Scenario) -> list[str]:
    errors: list[str] = []
    if not (scenario.name or "").strip():
        errors.append("Сценарий: укажите название.")
    if scenario.time_limit_mode not in ("auto", "manual"):
        errors.append("Сценарий: неизвестный режим лимита времени.")
    elif scenario.time_limit_mode == "manual" and int(scenario.time_limit_minutes or 0) < 1:
        errors.append("Сценарий: лимит времени должен быть не меньше 1 минуты.")
    if not scenario.attempts_unlimited:
        attempts = int(scenario.allowed_attempts or 0)
        if not 1 <= attempts <= MAX_ATTEMPTS:
            errors.append(
                f"Сценарий: число попыток должно быть от 1 до {MAX_ATTEMPTS}."
            )
    if scenario.selection_mode not in ("per_attempt", "per_participant"):
        errors.append("Сценарий: неизвестный режим выборки вопросов.")
    if scenario.grade_attempt_mode not in ("best", "last"):
        errors.append("Сценарий: неизвестный режим учёта попыток.")
    g3 = scenario.grade_3_min_percent
    g4 = scenario.grade_4_min_percent
    g5 = scenario.grade_5_min_percent
    if not 0 <= g3 < g4 < g5 <= 100:
        errors.append(
            "Сценарий: пороги оценок должны удовлетворять 0 ≤ «3» < «4» < «5» ≤ 100."
        )
    sample = scenario.questions_sample_size
    if sample is not None and int(sample) < 1:
        errors.append("Сценарий: размер выборки должен быть не меньше 1.")
    return errors


def _drafts_from_raw(questions: list) -> list[QuestionDraft]:
    return [
        QuestionDraft(
            text=item.get("text") or "",
            question_type=item.get("question_type") or QUESTION_SINGLE,
            options=[
                OptionDraft(o.get("text") or "", bool(o.get("is_correct")))
                for o in item.get("options") or []
            ],
        )
        for item in questions
    ]


def validate_package_dict(data: dict[str, Any]) -> list[str]:
    """Структурная проверка готового пакета — те же требования, что у плеера."""
    errors: list[str] = []
    if data.get("schema_version") != 3:
        errors.append("Пакет: ожидается schema_version=3.")
    if data.get("kind") != "room_package":
        errors.append('Пакет: ожидается kind="room_package".')
    quiz = data.get("quiz")
    if not isinstance(quiz, dict):
        return errors + ["Пакет: отсутствует блок quiz."]
    if not (quiz.get("title") or "").strip():
        errors.append("Пакет: пустое название теста.")
    room = data.get("room")
    if not isinstance(room, dict):
        return errors + ["Пакет: отсутствует блок room."]
    if not (room.get("name") or "").strip():
        errors.append("Пакет: пустое название сценария.")
    if not (room.get("public_id") or "").strip():
        errors.append("Пакет: пустой public_id.")

    total = 0
    if quiz.get("kind") == QUIZ_COMPOSITE:
        topics = quiz.get("topics")
        if not isinstance(topics, list) or not topics:
            errors.append("Мультитест: нет ни одной темы.")
            topics = []
        for topic in topics:
            if topic.get("topic_order") is None:
                errors.append("Мультитест: у темы нет topic_order.")
            questions = topic.get("questions") or []
            total += len(questions)
            errors.extend(
                validate_questions(
                    _drafts_from_raw(questions), f"Тема «{topic.get('title', '')}», "
                )
            )
    elif quiz.get("kind") == QUIZ_SINGLE:
        questions = quiz.get("questions") or []
        total += len(questions)
        errors.extend(validate_questions(_drafts_from_raw(questions)))
    else:
        errors.append("Пакет: неизвестный вид теста.")
    if total == 0:
        errors.append("В тесте нет вопросов.")
    return errors
