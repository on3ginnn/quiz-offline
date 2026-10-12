"""Кольцевой индикатор процента (QPainter)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget


class DonutChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._percent = 0
        self._accent = "#2E7D32"
        self._center_text: str | None = None
        self.setFixedSize(168, 168)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )

    def set_value(
        self,
        percent: float,
        accent_color: str,
        *,
        center_text: str | None = None,
    ) -> None:
        self._percent = max(0.0, min(100.0, float(percent)))
        self._accent = accent_color
        self._center_text = center_text
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        margin = 12
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        track = QPen(QColor("#D9E0E8"), 12)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawArc(rect, 0, 360 * 16)

        if self._percent > 0:
            progress = QPen(QColor(self._accent), 12)
            progress.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(progress)
            # Старт сверху (−90°), по часовой
            span = int(-self._percent / 100.0 * 360 * 16)
            painter.drawArc(rect, 90 * 16, span)

        painter.setPen(QColor(self._accent))
        font = QFont(self.font())
        font.setPointSize(26)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        center_label = (
            self._center_text
            if self._center_text is not None
            else f"{int(round(self._percent))}%"
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, center_label)
