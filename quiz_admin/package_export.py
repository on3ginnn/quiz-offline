"""Сборка пакета комнаты schema v3 (формат, который читает плеер)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from quiz_admin.models import (
    POLICY_FIELDS,
    QUIZ_COMPOSITE,
    QuestionDraft,
    Quiz,
    Scenario,
    Topic,
)
from quiz_admin.validation import (
    PackageValidationError,
    validate_package_dict,
    validate_scenario,
)


def _question_dict(question: QuestionDraft) -> dict[str, Any]:
    return {
        "text": question.text.strip(),
        "question_type": question.question_type,
        "options": [
            {"text": o.text.strip(), "is_correct": bool(o.is_correct)}
            for o in question.options
        ],
    }


def _policy_dict(scenario: Scenario, composite: bool) -> dict[str, Any]:
    room: dict[str, Any] = {
        "name": scenario.name.strip(),
        "public_id": scenario.public_id,
    }
    for name in POLICY_FIELDS:
        room[name] = getattr(scenario, name)
    if scenario.attempts_unlimited:
        room["allowed_attempts"] = None
    if scenario.time_limit_mode == "auto":
        room["time_limit_minutes"] = None
    if composite:
        room["questions_sample_size"] = None
    return room


def build_package_dict(
    quiz: Quiz,
    scenario: Scenario,
    *,
    questions: list[QuestionDraft] | None = None,
    topics: list[tuple[Topic, list[QuestionDraft]]] | None = None,
    quotas: dict[int, int] | None = None,
    exported_at: str | None = None,
) -> dict[str, Any]:
    """Собрать и проверить пакет; при проблемах — ``PackageValidationError``.

    ``quotas`` — {topic.id: question_count}; темы без записи берутся целиком.
    """
    composite = quiz.kind == QUIZ_COMPOSITE
    errors = validate_scenario(scenario)

    quiz_block: dict[str, Any] = {"title": quiz.title.strip(), "kind": quiz.kind}
    topic_quotas: list[dict[str, Any]] = []
    if composite:
        ordered = sorted(topics or [], key=lambda item: item[0].topic_order)
        quiz_block["topics"] = []
        for topic, topic_questions in ordered:
            quiz_block["topics"].append(
                {
                    "topic_order": topic.topic_order,
                    "title": topic.title.strip(),
                    "questions": [_question_dict(q) for q in topic_questions],
                }
            )
            if not topic_questions:
                errors.append(f"Тема «{topic.title}» не содержит вопросов.")
            quota = (quotas or {}).get(topic.id)
            if quota is not None:
                if quota < 0:
                    errors.append(
                        f"Тема «{topic.title}»: квота не может быть отрицательной."
                    )
                elif quota > len(topic_questions):
                    errors.append(
                        f"Тема «{topic.title}»: квота {quota} больше числа вопросов "
                        f"({len(topic_questions)})."
                    )
                topic_quotas.append(
                    {
                        "topic_order": topic.topic_order,
                        "topic_title": topic.title.strip(),
                        "question_count": int(quota),
                    }
                )
    else:
        bank = questions or []
        quiz_block["questions"] = [_question_dict(q) for q in bank]
        sample = scenario.questions_sample_size
        if sample is not None and int(sample) > len(bank):
            errors.append(
                f"Размер выборки {sample} больше числа вопросов ({len(bank)})."
            )

    package = {
        "schema_version": 3,
        "kind": "room_package",
        "exported_at": exported_at
        or datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "quiz": quiz_block,
        "room": _policy_dict(scenario, composite),
        "topic_quotas": topic_quotas,
    }
    errors.extend(validate_package_dict(package))
    if errors:
        raise PackageValidationError(list(dict.fromkeys(errors)))
    return package
