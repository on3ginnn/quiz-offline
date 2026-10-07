"""Форматирование дат и длительности для UI."""

from __future__ import annotations

from datetime import datetime


def format_datetime_ru(iso_value: str | None) -> str:
    if not iso_value:
        return "—"
    raw = iso_value.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return raw[:16].replace("T", " ")


def format_duration_short(sec: int | None) -> str:
    if sec is None:
        return "—"
    m, s = divmod(int(sec), 60)
    return f"{m} мин {s:02d} с"


def _attempts_word(n: int) -> str:
    tail = n % 10
    tail2 = n % 100
    if tail == 1 and tail2 != 11:
        return "попытка"
    if tail in (2, 3, 4) and tail2 not in (12, 13, 14):
        return "попытки"
    return "попыток"


def format_attempts_allowance(*, unlimited: bool, allowed: int | None) -> str:
    """Сколько попыток разрешено по политике комнаты."""
    if unlimited:
        return "без ограничения попыток"
    n = max(1, int(allowed or 1))
    return f"{n} {_attempts_word(n)}"


def format_questions_count(count: int) -> str:
    n = max(0, int(count))
    tail = n % 10
    tail2 = n % 100
    if tail == 1 and tail2 != 11:
        word = "вопрос"
    elif tail in (2, 3, 4) and tail2 not in (12, 13, 14):
        word = "вопроса"
    else:
        word = "вопросов"
    return f"{n} {word}"


def format_time_limit_minutes(minutes: int, *, auto: bool) -> str:
    mins = max(1, int(minutes))
    if auto:
        return f"{mins} мин (авто)"
    return f"{mins} мин"
