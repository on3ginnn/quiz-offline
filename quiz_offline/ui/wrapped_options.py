"""Варианты ответа с переносом длинного текста (QRadioButton/QCheckBox сами не wrap)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QWidget,
)


class _ClickableLabel(QLabel):
    """Клик по тексту переключает связанную кнопку выбора."""

    def __init__(self, text: str, button, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._button = button
        self.setWordWrap(True)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._button is not None:
            if isinstance(self._button, QCheckBox):
                self._button.setChecked(not self._button.isChecked())
            else:
                self._button.setChecked(True)
        super().mouseReleaseEvent(event)


def build_single_choice_row(
    text: str, *, checked: bool, parent: QWidget
) -> tuple[QWidget, QRadioButton]:
    row = QWidget(parent)
    row.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 4, 0, 4)
    layout.setSpacing(10)
    rb = QRadioButton(row)
    rb.setChecked(checked)
    label = _ClickableLabel(text, rb, row)
    label.setObjectName("optionText")
    layout.addWidget(rb, alignment=Qt.AlignmentFlag.AlignTop)
    layout.addWidget(label, stretch=1)
    return row, rb


def build_multiple_choice_row(
    text: str, *, checked: bool, parent: QWidget
) -> tuple[QWidget, QCheckBox]:
    row = QWidget(parent)
    row.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
    )
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 4, 0, 4)
    layout.setSpacing(10)
    cb = QCheckBox(row)
    cb.setChecked(checked)
    label = _ClickableLabel(text, cb, row)
    label.setObjectName("optionText")
    layout.addWidget(cb, alignment=Qt.AlignmentFlag.AlignTop)
    layout.addWidget(label, stretch=1)
    return row, cb
