"""Разделитель, который при нехватке ширины (крупный текст) раскладывает панели вертикально."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QWidget


class ResponsiveSplitter(QSplitter):
    """Горизонтально, пока хватает места; иначе — друг под другом.

    ``narrow_lines`` — порог ширины в высотах строки текста (растёт вместе с масштабом).
    ``vertical_min_lines`` — минимальная высота каждой панели в вертикальном режиме.
    """

    def __init__(self, narrow_lines: int, vertical_min_lines: list[int]) -> None:
        super().__init__(Qt.Orientation.Horizontal)
        self.setChildrenCollapsible(False)
        self._narrow_lines = narrow_lines
        self._vertical_min_lines = vertical_min_lines

    def _apply(self) -> None:
        line = self.fontMetrics().height()
        vertical = self.width() < line * self._narrow_lines
        want = Qt.Orientation.Vertical if vertical else Qt.Orientation.Horizontal
        if self.orientation() != want:
            self.setOrientation(want)
        for i in range(self.count()):
            child: QWidget = self.widget(i)
            lines = self._vertical_min_lines[i] if i < len(self._vertical_min_lines) else 0
            child.setMinimumHeight(line * lines if vertical else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply()
