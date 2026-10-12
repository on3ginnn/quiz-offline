"""Панель «Размер текста» (А− / 100% / А+) и применение масштаба к приложению."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget

from quiz_offline.ui.theme import (
    DEFAULT_SCALE,
    app_stylesheet,
    clamp_scale,
    load_scale,
    next_scale,
    save_scale,
)


def apply_scale(scale: float) -> float:
    """Применить масштаб ко всему приложению и сохранить выбор."""
    scale = clamp_scale(scale)
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(app_stylesheet(scale))
    save_scale(scale)
    return scale


class ScaleBar(QWidget):
    scale_changed = pyqtSignal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scale = load_scale()

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        caption = QLabel("Размер текста:")
        caption.setObjectName("subtitle")
        row.addWidget(caption)

        self.smaller_btn = QPushButton("А−")
        self.smaller_btn.setObjectName("scaleBtn")
        self.smaller_btn.setToolTip("Уменьшить текст (Ctrl+−)")
        self.smaller_btn.clicked.connect(lambda: self.step(-1))
        row.addWidget(self.smaller_btn)

        self.value_label = QLabel()
        self.value_label.setMinimumWidth(48)
        row.addWidget(self.value_label)

        self.larger_btn = QPushButton("А+")
        self.larger_btn.setObjectName("scaleBtn")
        self.larger_btn.setToolTip("Увеличить текст (Ctrl+=)")
        self.larger_btn.clicked.connect(lambda: self.step(1))
        row.addWidget(self.larger_btn)

        for keys, handler in (
            ("Ctrl+=", lambda: self.step(1)),
            ("Ctrl++", lambda: self.step(1)),
            ("Ctrl+-", lambda: self.step(-1)),
            ("Ctrl+0", lambda: self.set_scale(DEFAULT_SCALE)),
        ):
            QShortcut(QKeySequence(keys), self, activated=handler)

        self._refresh()

    @property
    def scale(self) -> float:
        return self._scale

    def step(self, direction: int) -> None:
        self.set_scale(next_scale(self._scale, direction))

    def set_scale(self, scale: float) -> None:
        scale = clamp_scale(scale)
        if scale == self._scale:
            return
        self._scale = apply_scale(scale)
        self._refresh()
        self.scale_changed.emit(self._scale)

    def _refresh(self) -> None:
        self.value_label.setText(f"{round(self._scale * 100)}%")
        self.smaller_btn.setEnabled(self._scale > min(next_scale(self._scale, -1), self._scale))
        self.larger_btn.setEnabled(self._scale < next_scale(self._scale, 1))
