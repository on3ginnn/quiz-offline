"""Вспомогательные функции для PyQt6-виджетов."""

from __future__ import annotations

from PyQt6.QtCore import Qt


def is_checkbox_checked(state) -> bool:
    """PyQt6: stateChanged передаёт Qt.CheckState, не int."""
    if isinstance(state, Qt.CheckState):
        return state == Qt.CheckState.Checked
    return state == Qt.CheckState.Checked.value
