"""Строка мета-бейджей (компактные подписи политики комнаты)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget


class MetaBadgesRow(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def set_labels(
        self,
        labels: list[str],
        *,
        tooltips: list[str | None] | None = None,
    ) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        tips = tooltips or []
        for i, text in enumerate(labels):
            if not text:
                continue
            badge = QLabel(text)
            badge.setObjectName("metaBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if i < len(tips) and tips[i]:
                badge.setToolTip(tips[i])
            self._layout.addWidget(badge)
        self._layout.addStretch()
        self.setVisible(bool(labels))
