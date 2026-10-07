"""Порт select_attempt_questions для офлайн-пакета."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from quiz_offline.models import AttemptLayoutItem, Question, RoomPackage

if TYPE_CHECKING:
    from quiz_offline.models import RoomPolicy


def quotas_by_topic_order(package: RoomPackage) -> dict[int, int]:
    return {q.topic_order: q.question_count for q in package.topic_quotas}


def effective_time_limit_minutes(room: RoomPolicy, question_count: int) -> int:
    """Лимит минут: авто = 1 мин на вопрос, иначе ручной."""
    if (room.time_limit_mode or "auto").strip() == "auto":
        return max(1, int(question_count or 0) or 1)
    return int(room.time_limit_minutes or 1)


def _fixed_or_random_sample(
    stored: dict[int, list[int]] | None,
    topic_key: int,
    pool: list[Question],
    count: int,
    *,
    persist: bool,
) -> list[Question]:
    pool_by_id = {q.id: q for q in pool}
    chosen: list[Question] = []
    if stored and topic_key in stored and stored[topic_key]:
        chosen = [
            pool_by_id[qid] for qid in stored[topic_key] if qid in pool_by_id
        ]
    if len(chosen) < count:
        chosen_ids = {q.id for q in chosen}
        remaining = [q for q in pool if q.id not in chosen_ids]
        random.shuffle(remaining)
        chosen += remaining[: count - len(chosen)]
    chosen = chosen[:count]
    if persist and stored is not None:
        stored[topic_key] = [q.id for q in chosen]
    return chosen


def select_attempt_questions(
    package: RoomPackage,
    participant_selections: dict[int, list[int]] | None = None,
) -> list[tuple[Question, int | None]]:
    """
    Вернуть список (question, topic_order) для раскладки попытки.
    participant_selections мутируется при selection_mode=per_participant.
    """
    room = package.room
    if room is None:
        raise ValueError("В пакете нет настроек комнаты.")

    per_participant = room.selection_mode == "per_participant"
    stored = participant_selections if per_participant else None

    if package.quiz_kind == "composite":
        quotas = quotas_by_topic_order(package)
        result: list[tuple[Question, int | None]] = []
        for topic_order in sorted(package.topics.keys()):
            pool = list(package.topics[topic_order])
            quota = quotas.get(topic_order)
            if quota is None:
                chosen = pool
            else:
                quota = int(quota)
                if quota <= 0:
                    continue
                if quota > len(pool):
                    raise ValueError(
                        f"В теме «{topic_order}» недостаточно вопросов "
                        f"({len(pool)}) для квоты {quota}."
                    )
                chosen = _fixed_or_random_sample(
                    stored,
                    topic_order,
                    pool,
                    quota,
                    persist=per_participant,
                )
            for q in chosen:
                result.append((q, topic_order))
        if room.shuffle_questions:
            random.shuffle(result)
        return result

    questions = list(package.questions)
    bank_n = len(questions)
    sample_n = room.questions_sample_size
    if sample_n and bank_n and int(sample_n) < bank_n:
        questions = _fixed_or_random_sample(
            stored,
            0,
            questions,
            int(sample_n),
            persist=per_participant,
        )
    if room.shuffle_questions:
        random.shuffle(questions)
    else:
        questions.sort(key=lambda q: q.id)
    return [(q, None) for q in questions]


def build_attempt_layout(
    package: RoomPackage,
    participant_selections: dict[int, list[int]] | None = None,
) -> list[AttemptLayoutItem]:
    """Раскладка попытки с порядком вариантов (shuffle_options)."""
    room = package.room
    if room is None:
        raise ValueError("В пакете нет настроек комнаты.")
    selected = select_attempt_questions(package, participant_selections)
    layout: list[AttemptLayoutItem] = []
    for question, topic_order in selected:
        option_ids = [o.id for o in question.options]
        if room.shuffle_options and len(option_ids) > 1:
            random.shuffle(option_ids)
        layout.append(
            AttemptLayoutItem(
                question=question,
                topic_order=topic_order,
                option_ids_order=option_ids,
            )
        )
    return layout
