"""Парсинг и валидация JSON-пакета комнаты (schema v3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quiz_offline.models import (
    AnswerOption,
    Question,
    RoomPackage,
    RoomPolicy,
    TopicQuota,
)

ALLOWED_QUESTION_TYPES = frozenset({"single", "multiple"})


class RoomPackageError(ValueError):
    """Невалидный пакет комнаты."""


def normalize_full_name(display: str) -> str:
    return " ".join((display or "").split()).casefold()


def _parse_options(raw_options: list, question_id: int) -> list[AnswerOption]:
    if not isinstance(raw_options, list) or len(raw_options) < 2:
        raise RoomPackageError(
            f"Вопрос {question_id}: нужно минимум 2 варианта ответа."
        )
    options: list[AnswerOption] = []
    for idx, item in enumerate(raw_options, start=1):
        if not isinstance(item, dict):
            raise RoomPackageError(f"Вопрос {question_id}: неверный вариант.")
        text = (item.get("text") or "").strip()
        if not text:
            raise RoomPackageError(f"Вопрос {question_id}: пустой текст варианта.")
        options.append(
            AnswerOption(
                id=question_id * 100 + idx,
                text=text,
                is_correct=bool(item.get("is_correct")),
            )
        )
    if not any(o.is_correct for o in options):
        raise RoomPackageError(
            f"Вопрос {question_id}: нет правильного варианта."
        )
    return options


def _parse_questions(raw_questions: list, topic_order: int | None) -> list[Question]:
    if not isinstance(raw_questions, list):
        raise RoomPackageError("questions должен быть массивом.")
    result: list[Question] = []
    for q_idx, item in enumerate(raw_questions, start=1):
        if not isinstance(item, dict):
            raise RoomPackageError("Неверный формат вопроса.")
        text = (item.get("text") or "").strip()
        if not text:
            raise RoomPackageError("Пустой текст вопроса.")
        qtype = (item.get("question_type") or "single").strip().lower()
        if qtype not in ALLOWED_QUESTION_TYPES:
            raise RoomPackageError(f"Неизвестный тип вопроса: {qtype}")
        base_id = (topic_order or 0) * 10_000 + q_idx
        options = _parse_options(item.get("options") or [], base_id)
        result.append(
            Question(
                id=base_id,
                text=text,
                question_type=qtype,
                options=options,
                topic_order=topic_order,
            )
        )
    return result


def _parse_room_policy(raw: dict) -> RoomPolicy:
    public_id = (raw.get("public_id") or "").strip()
    if not public_id:
        raise RoomPackageError("room.public_id обязателен.")
    name = (raw.get("name") or "").strip()
    if not name:
        raise RoomPackageError("room.name обязателен.")
    return RoomPolicy(
        name=name,
        public_id=public_id,
        time_limit_mode=(raw.get("time_limit_mode") or "auto").strip(),
        time_limit_minutes=raw.get("time_limit_minutes"),
        attempts_unlimited=bool(raw.get("attempts_unlimited")),
        allowed_attempts=raw.get("allowed_attempts"),
        shuffle_questions=bool(raw.get("shuffle_questions")),
        shuffle_options=bool(raw.get("shuffle_options")),
        selection_mode=(raw.get("selection_mode") or "per_attempt").strip(),
        show_results=bool(raw.get("show_results", True)),
        show_answers=bool(raw.get("show_answers")),
        show_correct_answers=bool(raw.get("show_correct_answers")),
        grade_3_min_percent=int(raw.get("grade_3_min_percent") or 70),
        grade_4_min_percent=int(raw.get("grade_4_min_percent") or 80),
        grade_5_min_percent=int(raw.get("grade_5_min_percent") or 90),
        grade_attempt_mode=(raw.get("grade_attempt_mode") or "best").strip(),
        questions_sample_size=raw.get("questions_sample_size"),
    )


def parse_room_package_dict(data: dict[str, Any]) -> RoomPackage:
    if int(data.get("schema_version", 0)) != 3:
        raise RoomPackageError("Ожидается schema_version=3.")
    if data.get("kind") != "room_package":
        raise RoomPackageError('Ожидается kind="room_package".')

    quiz_raw = data.get("quiz")
    if not isinstance(quiz_raw, dict):
        raise RoomPackageError("Отсутствует блок quiz.")

    quiz_kind = (quiz_raw.get("kind") or "single").strip()
    quiz_title = (quiz_raw.get("title") or "").strip()
    if not quiz_title:
        raise RoomPackageError("quiz.title обязателен.")

    room = _parse_room_policy(data.get("room") or {})
    topic_quotas: list[TopicQuota] = []
    for item in data.get("topic_quotas") or []:
        if not isinstance(item, dict):
            continue
        topic_quotas.append(
            TopicQuota(
                topic_order=int(item.get("topic_order") or 0),
                topic_title=(item.get("topic_title") or "").strip(),
                question_count=int(item.get("question_count") or 0),
            )
        )

    package = RoomPackage(
        exported_at=str(data.get("exported_at") or ""),
        quiz_title=quiz_title,
        quiz_kind=quiz_kind,
        room=room,
        topic_quotas=topic_quotas,
        raw=data,
    )

    if quiz_kind == "composite":
        topics_raw = quiz_raw.get("topics")
        if not isinstance(topics_raw, list) or not topics_raw:
            raise RoomPackageError("В мультитесте нет тем.")
        for topic in topics_raw:
            if not isinstance(topic, dict):
                raise RoomPackageError("Неверный формат темы.")
            order = topic.get("topic_order")
            if order is None:
                raise RoomPackageError("topic_order обязателен в темах.")
            order_int = int(order)
            questions = _parse_questions(topic.get("questions") or [], order_int)
            package.topics[order_int] = questions
            package.questions.extend(questions)
    else:
        package.questions = _parse_questions(quiz_raw.get("questions") or [], None)

    if not package.questions:
        raise RoomPackageError("В пакете нет вопросов.")

    return package


def load_room_package_from_path(path: Path) -> RoomPackage:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RoomPackageError(f"Не удалось прочитать файл: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RoomPackageError("Файл не является валидным JSON.") from exc
    if not isinstance(data, dict):
        raise RoomPackageError("Корень JSON должен быть объектом.")
    return parse_room_package_dict(data)
