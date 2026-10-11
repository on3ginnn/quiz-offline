"""Импорт тестов из JSON: schema 1 (тест / массив вопросов), 2 (мультитест), 3 (пакет)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quiz_admin.models import (
    POLICY_FIELDS,
    QUESTION_SINGLE,
    QUIZ_COMPOSITE,
    QUIZ_SINGLE,
    OptionDraft,
    QuestionDraft,
)
from quiz_admin.validation import validate_questions


class ImportDataError(ValueError):
    """Файл нельзя импортировать; ``errors`` — список причин."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass
class ImportedTopic:
    topic_order: int
    title: str
    questions: list[QuestionDraft]


@dataclass
class ImportedQuiz:
    title: str
    kind: str
    questions: list[QuestionDraft] = field(default_factory=list)
    topics: list[ImportedTopic] = field(default_factory=list)
    scenario_name: str | None = None
    policy: dict[str, Any] = field(default_factory=dict)
    quotas: dict[int, int] = field(default_factory=dict)  # topic_order -> count


def _parse_questions(raw: Any, prefix: str = "") -> list[QuestionDraft]:
    if not isinstance(raw, list):
        raise ImportDataError([f"{prefix}questions должен быть массивом."])
    result: list[QuestionDraft] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ImportDataError([f"{prefix}неверный формат вопроса."])
        options = [
            OptionDraft(str(o.get("text") or "").strip(), bool(o.get("is_correct")))
            for o in item.get("options") or []
            if isinstance(o, dict)
        ]
        result.append(
            QuestionDraft(
                text=str(item.get("text") or "").strip(),
                question_type=str(item.get("question_type") or QUESTION_SINGLE)
                .strip()
                .lower(),
                options=options,
            )
        )
    errors = validate_questions(result, prefix)
    if errors:
        raise ImportDataError(errors)
    return result


def parse_import(data: Any, default_title: str = "Импортированный тест") -> ImportedQuiz:
    if isinstance(data, list):
        return ImportedQuiz(
            title=default_title, kind=QUIZ_SINGLE, questions=_parse_questions(data)
        )
    if not isinstance(data, dict):
        raise ImportDataError(["Корень JSON должен быть объектом или массивом вопросов."])

    if data.get("kind") == "room_package":
        return _parse_room_package(data)

    title = str(data.get("title") or default_title).strip() or default_title
    topics_raw = data.get("topics")
    if data.get("kind") == QUIZ_COMPOSITE or isinstance(topics_raw, list):
        if not isinstance(topics_raw, list) or not topics_raw:
            raise ImportDataError(["В мультитесте нет тем."])
        topics = [
            ImportedTopic(
                topic_order=idx,
                title=str(t.get("title") or "").strip() or f"Тема {idx}",
                questions=_parse_questions(t.get("questions") or [], f"Тема {idx}: "),
            )
            for idx, t in enumerate(topics_raw, start=1)
            if isinstance(t, dict)
        ]
        return ImportedQuiz(title=title, kind=QUIZ_COMPOSITE, topics=topics)
    return ImportedQuiz(
        title=title, kind=QUIZ_SINGLE, questions=_parse_questions(data.get("questions") or [])
    )


def _parse_room_package(data: dict[str, Any]) -> ImportedQuiz:
    if data.get("schema_version") != 3:
        raise ImportDataError(["Ожидается schema_version=3."])
    quiz = data.get("quiz")
    if not isinstance(quiz, dict):
        raise ImportDataError(["Отсутствует блок quiz."])
    title = str(quiz.get("title") or "").strip() or "Импортированный тест"
    room = data.get("room") if isinstance(data.get("room"), dict) else {}
    imported = ImportedQuiz(
        title=title,
        kind=QUIZ_COMPOSITE if quiz.get("kind") == QUIZ_COMPOSITE else QUIZ_SINGLE,
        scenario_name=str(room.get("name") or "").strip() or "Сценарий",
        policy={k: room[k] for k in POLICY_FIELDS if k in room},
    )
    if imported.kind == QUIZ_COMPOSITE:
        for t in quiz.get("topics") or []:
            order = int(t.get("topic_order") or 0)
            imported.topics.append(
                ImportedTopic(
                    order,
                    str(t.get("title") or "").strip() or f"Тема {order}",
                    _parse_questions(t.get("questions") or [], f"Тема {order}: "),
                )
            )
        for item in data.get("topic_quotas") or []:
            imported.quotas[int(item.get("topic_order") or 0)] = int(
                item.get("question_count") or 0
            )
    else:
        imported.questions = _parse_questions(quiz.get("questions") or [])
    return imported


def load_import_file(path: Path) -> ImportedQuiz:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ImportDataError([f"Не удалось прочитать файл: {path}"]) from exc
    except json.JSONDecodeError as exc:
        raise ImportDataError(["Файл не является валидным JSON."]) from exc
    return parse_import(data, default_title=path.stem)
