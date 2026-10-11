"""Операции над тестами: сохранение, клонирование, объединение, импорт, выгрузка."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from quiz_admin.importers import ImportedQuiz, ImportDataError
from quiz_admin.models import (
    POLICY_FIELDS,
    QUIZ_COMPOSITE,
    QUIZ_SINGLE,
    QuestionDraft,
    Quiz,
    Scenario,
)
from quiz_admin.package_export import build_package_dict
from quiz_admin.storage import AdminStorage
from quiz_admin.validation import PackageValidationError, validate_questions


def _copy_questions(questions: list[QuestionDraft]) -> list[QuestionDraft]:
    return [
        QuestionDraft(
            q.text,
            q.question_type,
            [replace(o) for o in q.options],
        )
        for q in questions
    ]


def save_questions(
    storage: AdminStorage,
    quiz_id: int,
    topic_id: int | None,
    questions: list[QuestionDraft],
) -> None:
    """Проверить и сохранить банк вопросов теста (одиночный) или темы."""
    if topic_id is None and storage.quiz_is_composite(quiz_id):
        raise PackageValidationError(
            ["У мультитеста нет своих вопросов — редактируйте вопросы тем."]
        )
    errors = validate_questions(questions)
    if errors:
        raise PackageValidationError(errors)
    storage.replace_questions(quiz_id, topic_id, questions)


def add_topic_from_quiz(
    storage: AdminStorage,
    composite_id: int,
    source_quiz_id: int,
    title: str | None = None,
) -> int:
    """Добавить тему в мультитест, клонировав вопросы обычного теста. Возвращает topic.id."""
    composite = storage.get_quiz(composite_id)
    source = storage.get_quiz(source_quiz_id)
    if composite is None or composite.kind != QUIZ_COMPOSITE:
        raise ValueError("Тема добавляется только в мультитест.")
    if source is None or source.kind != QUIZ_SINGLE:
        raise ValueError("Источником темы может быть только обычный тест.")
    topic = storage.add_topic(composite_id, (title or source.title).strip() or source.title)
    storage.replace_questions(
        composite_id, topic.id, _copy_questions(storage.list_questions(source_quiz_id))
    )
    return topic.id


def merge_quizzes(storage: AdminStorage, title: str, source_ids: list[int]) -> Quiz:
    """Объединить обычные тесты в новый мультитест: каждый тест — отдельная тема."""
    if len(source_ids) < 2:
        raise ValueError("Для объединения выберите минимум два теста.")
    composite = storage.create_quiz(title, QUIZ_COMPOSITE)
    for source_id in source_ids:
        add_topic_from_quiz(storage, composite.id, source_id)
    return composite


def duplicate_quiz(storage: AdminStorage, quiz_id: int) -> Quiz:
    """Глубокая копия теста вместе с темами и вопросами (сценарии не копируются)."""
    source = storage.get_quiz(quiz_id)
    if source is None:
        raise ValueError("Тест не найден.")
    copy = storage.create_quiz(f"{source.title} (копия)", source.kind)
    if source.kind == QUIZ_COMPOSITE:
        for topic in storage.list_topics(quiz_id):
            new_topic = storage.add_topic(copy.id, topic.title)
            storage.replace_questions(
                copy.id,
                new_topic.id,
                _copy_questions(storage.list_questions(quiz_id, topic.id)),
            )
    else:
        storage.replace_questions(
            copy.id, None, _copy_questions(storage.list_questions(quiz_id))
        )
    return copy


def duplicate_scenario(storage: AdminStorage, scenario_id: int) -> Scenario:
    source = storage.get_scenario(scenario_id)
    if source is None:
        raise ValueError("Сценарий не найден.")
    policy = {name: getattr(source, name) for name in POLICY_FIELDS}
    copy = storage.create_scenario(source.quiz_id, f"{source.name} (копия)", **policy)
    storage.set_quotas(copy.id, storage.get_quotas(source.id))
    return copy


def import_quiz(storage: AdminStorage, imported: ImportedQuiz) -> Quiz:
    """Создать тест (и сценарий, если он был в файле) из разобранного импорта."""
    if imported.kind == QUIZ_COMPOSITE and not imported.topics:
        raise ImportDataError(["В мультитесте нет тем."])
    quiz = storage.create_quiz(imported.title, imported.kind)
    topic_ids: dict[int, int] = {}
    if imported.kind == QUIZ_COMPOSITE:
        for topic in imported.topics:
            created = storage.add_topic(quiz.id, topic.title)
            topic_ids[topic.topic_order] = created.id
            storage.replace_questions(quiz.id, created.id, topic.questions)
    else:
        storage.replace_questions(quiz.id, None, imported.questions)
    if imported.scenario_name:
        scenario = storage.create_scenario(quiz.id, imported.scenario_name, **imported.policy)
        quotas = {
            topic_ids[order]: count
            for order, count in imported.quotas.items()
            if order in topic_ids
        }
        storage.set_quotas(scenario.id, quotas)
    return quiz


def build_package(storage: AdminStorage, scenario_id: int) -> dict[str, Any]:
    """Собрать пакет для плеера; ``PackageValidationError`` — если есть проблемы."""
    scenario = storage.get_scenario(scenario_id)
    if scenario is None:
        raise PackageValidationError(["Сценарий не найден."])
    quiz = storage.get_quiz(scenario.quiz_id)
    if quiz is None:
        raise PackageValidationError(["Тест не найден."])
    if quiz.kind == QUIZ_COMPOSITE:
        topics = [
            (t, storage.list_questions(quiz.id, t.id)) for t in storage.list_topics(quiz.id)
        ]
        return build_package_dict(
            quiz, scenario, topics=topics, quotas=storage.get_quotas(scenario.id)
        )
    return build_package_dict(quiz, scenario, questions=storage.list_questions(quiz.id))


def suggested_filename(quiz: Quiz, scenario: Scenario) -> str:
    raw = f"{quiz.title}-{scenario.name}"
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", raw).strip("._")
    return f"{cleaned or 'package'}.json"


def export_package(storage: AdminStorage, scenario_id: int, path: Path) -> None:
    package = build_package(storage, scenario_id)
    path.write_text(
        json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
