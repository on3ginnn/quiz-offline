"""Варианты ответа: крупные карточки с переносом длинного текста."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSizePolicy,
    QWidget,
)


def _set_flag(widget: QWidget, name: str, value: bool) -> None:
    widget.setProperty(name, value)
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


class _OptionCard(QFrame):
    """Карточка варианта: клик в любом месте переключает кнопку выбора."""

    def __init__(
        self, text: str, button: QAbstractButton, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("optionCard")
        self._button = button
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        button.setParent(self)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignVCenter)
        label = QLabel(text)
        label.setObjectName("optionText")
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(label, stretch=1)

        _set_flag(self, "selected", button.isChecked())
        _set_flag(self, "focused", False)
        button.toggled.connect(lambda checked: _set_flag(self, "selected", checked))
        button.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if obj is self._button:
            if event.type() == QEvent.Type.FocusIn:
                _set_flag(self, "focused", True)
            elif event.type() == QEvent.Type.FocusOut:
                _set_flag(self, "focused", False)
        return super().eventFilter(obj, event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if isinstance(self._button, QCheckBox):
                self._button.setChecked(not self._button.isChecked())
            else:
                self._button.setChecked(True)
            self._button.setFocus()
        super().mouseReleaseEvent(event)


def build_single_choice_row(
    text: str, *, checked: bool, parent: QWidget
) -> tuple[QWidget, QRadioButton]:
    rb = QRadioButton()
    rb.setChecked(checked)
    return _OptionCard(text, rb, parent), rb


def build_multiple_choice_row(
    text: str, *, checked: bool, parent: QWidget
) -> tuple[QWidget, QCheckBox]:
    cb = QCheckBox()
    cb.setChecked(checked)
    return _OptionCard(text, cb, parent), cb
