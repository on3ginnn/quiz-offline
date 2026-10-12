"""Цепочка фокуса для клавиатурной навигации на экране прохождения."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget


def is_widget_focusable(widget: QWidget) -> bool:
    """Виджет участвует в цепочке: виден, включён, может получить фокус."""
    if not widget.isVisible():
        return False
    if not widget.isEnabled():
        return False
    if widget.focusPolicy() == Qt.FocusPolicy.NoFocus:
        return False
    return True


def build_taking_focus_chain(
    option_buttons: list[QWidget],
    next_btn: QWidget,
    prev_btn: QWidget,
    clear_btn: QWidget,
) -> list[QWidget]:
    """Порядок: варианты → Далее → Назад → Очистить."""
    chain: list[QWidget] = []
    for btn in option_buttons:
        if is_widget_focusable(btn):
            chain.append(btn)
    for widget in (next_btn, prev_btn, clear_btn):
        if is_widget_focusable(widget):
            chain.append(widget)
    return chain


def move_focus_in_chain(
    chain: list[QWidget],
    current: QWidget | None,
    delta: int,
) -> QWidget | None:
    """Циклический переход по цепочке; delta +1 — вниз, −1 — вверх."""
    if not chain:
        return None
    if current is None or current not in chain:
        target = chain[0] if delta >= 0 else chain[-1]
        target.setFocus()
        return target
    idx = chain.index(current)
    next_idx = (idx + delta) % len(chain)
    target = chain[next_idx]
    target.setFocus()
    return target
