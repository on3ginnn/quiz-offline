"""Метаданные комнаты из пакета для бейджей Home и зала."""

from __future__ import annotations

from dataclasses import dataclass

from quiz_offline.models import RoomPackage
from quiz_offline.selection import effective_time_limit_minutes, quotas_by_topic_order
from quiz_offline.ui.formatters import (
    format_attempts_allowance,
    format_questions_count,
    format_time_limit_minutes,
)


@dataclass(frozen=True)
class RoomCardMeta:
    quiz_kind: str
    hall_badges: list[str]
    home_badges: list[str]


def estimate_questions_per_attempt(package: RoomPackage) -> int:
    """Число вопросов за попытку без shuffle (для подписи в UI)."""
    room = package.room
    if room is None:
        return 0

    if package.quiz_kind == "composite":
        quotas = quotas_by_topic_order(package)
        total = 0
        for topic_order in sorted(package.topics.keys()):
            pool = package.topics[topic_order]
            quota = quotas.get(topic_order)
            if quota is None:
                total += len(pool)
            else:
                total += max(0, int(quota))
        return total

    bank_n = len(package.questions)
    sample_n = room.questions_sample_size
    if sample_n and bank_n and int(sample_n) < bank_n:
        return int(sample_n)
    return bank_n


def build_room_meta_labels(package: RoomPackage) -> list[str]:
    """Полный набор бейджей политики комнаты для зала."""
    room = package.room
    if room is None:
        return []

    question_count = estimate_questions_per_attempt(package)
    minutes = effective_time_limit_minutes(room, question_count)
    auto_time = (room.time_limit_mode or "auto").strip() == "auto"

    labels = [
        format_attempts_allowance(
            unlimited=room.attempts_unlimited,
            allowed=room.allowed_attempts,
        ),
        format_time_limit_minutes(minutes, auto=auto_time),
        format_questions_count(question_count),
    ]
    if package.quiz_kind == "composite" and package.topics:
        topic_n = len(package.topics)
        tail = topic_n % 10
        tail2 = topic_n % 100
        if tail == 1 and tail2 != 11:
            word = "тема"
        elif tail in (2, 3, 4) and tail2 not in (12, 13, 14):
            word = "темы"
        else:
            word = "тем"
        labels.append(f"{topic_n} {word}")
    return labels


def build_room_card_meta(
    package: RoomPackage | None,
    *,
    tested_participant_count: int,
) -> RoomCardMeta:
    """Мета для карточки на главной: попытки и число прошедших первыми, затем время и вопросы."""
    kind = "single"
    if package is None:
        return RoomCardMeta(
            quiz_kind=kind,
            hall_badges=[],
            home_badges=[f"Прошли: {tested_participant_count}"],
        )

    kind = package.quiz_kind or "single"
    hall_badges = build_room_meta_labels(package)
    home_badges: list[str] = []
    if hall_badges:
        home_badges.append(hall_badges[0])
    home_badges.append(f"Прошли: {tested_participant_count}")
    if len(hall_badges) >= 3:
        home_badges.extend(hall_badges[1:3])
    return RoomCardMeta(
        quiz_kind=kind,
        hall_badges=hall_badges,
        home_badges=home_badges,
    )
