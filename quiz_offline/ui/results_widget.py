"""Экран результатов попытки."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_offline.ui.donut_chart import DonutChart
from quiz_offline.ui.result_visual import format_grade_scale_caption, outcome_for_percent


class ResultsWidget(QWidget):
    retry = pyqtSignal()
    leave_test = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._context: dict | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        center = QHBoxLayout()
        center.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("resultCard")
        self.card.setMaximumWidth(640)
        card = QVBoxLayout(self.card)
        card.setContentsMargins(28, 24, 28, 20)
        card.setSpacing(16)

        top_row = QHBoxLayout()
        top_row.setSpacing(24)

        # Оценка (5-балльная) + кольцо процентов — одна колонка
        grade_col = QVBoxLayout()
        grade_col.setSpacing(10)
        grade_col.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.grade_label = QLabel()
        self.grade_label.setObjectName("gradeResult")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grade_col.addWidget(self.grade_label)

        self.donut = DonutChart()
        grade_col.addWidget(self.donut, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.percent_caption = QLabel()
        self.percent_caption.setWordWrap(True)
        self.percent_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.percent_caption.setObjectName("resultPercentCaption")
        grade_col.addWidget(self.percent_caption)

        top_row.addLayout(grade_col, stretch=1)

        # Время — отдельная метрика справа
        time_col = QVBoxLayout()
        time_col.setSpacing(4)
        time_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_value_lbl = QLabel("⏱  —")
        self.time_value_lbl.setObjectName("resultMetricValue")
        self.time_value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_caption = QLabel("время прохождения")
        time_caption.setObjectName("subtitle")
        time_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_col.addWidget(self.time_value_lbl)
        time_col.addWidget(time_caption)
        top_row.addLayout(time_col, stretch=1)

        card.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        self.hint = QLabel()
        self.hint.setObjectName("subtitle")
        self.hint.setWordWrap(True)
        bottom_row.addWidget(self.hint, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.leave_btn = QPushButton("Покинуть тест")
        self.leave_btn.setObjectName("resultBtn")
        self.leave_btn.setMinimumWidth(156)
        self.leave_btn.clicked.connect(self.leave_test.emit)
        self.retry_btn = QPushButton("Пройти ещё раз")
        self.retry_btn.setObjectName("primary")
        self.retry_btn.setMinimumWidth(156)
        self.retry_btn.clicked.connect(self.retry.emit)
        actions.addWidget(self.leave_btn)
        actions.addWidget(self.retry_btn)
        bottom_row.addLayout(actions)
        card.addLayout(bottom_row)

        center.addWidget(self.card)
        center.addStretch(1)
        outer.addLayout(center)
        outer.addStretch(1)

    def show_result(self, context: dict) -> None:
        self._context = context
        result = context["result"]
        remaining = context.get("remaining_attempts")
        visual = outcome_for_percent(result.weighted_percent)
        grade = result.grade

        self.card.setStyleSheet(
            f"QFrame#resultCard {{ background: {visual.bg}; border: 1px solid #dbdbdb;"
            f" border-radius: 12px; }}"
        )
        self.grade_label.setText(f"Оценка {grade}")
        self.grade_label.setStyleSheet(
            f"font-size: 32px; font-weight: 700; color: {visual.color};"
            f" background: transparent;"
        )

        self.donut.set_value(
            result.weighted_percent,
            visual.color,
            center_text=str(grade),
        )
        self.percent_caption.setTextFormat(Qt.TextFormat.RichText)
        grade_caption = format_grade_scale_caption(grade)
        self.percent_caption.setText(
            f"<span style='color:{visual.color}; font-weight:600; font-size:16px;'>"
            f"{grade_caption}</span>"
            f" <span style='color:#646464;'>баллов по 5-балльной шкале</span>"
        )

        mins, secs = divmod(int(result.duration_sec), 60)
        self.time_value_lbl.setText(f"⏱  {mins}:{secs:02d}")
        self.time_value_lbl.setStyleSheet(
            f"font-size: 22px; font-weight: 600; color: {visual.color};"
            f" background: transparent;"
        )

        if context.get("finished_by_timer"):
            self.hint.setText("Время истекло — ответы отправлены автоматически.")
        elif remaining is None:
            self.hint.setText("Попытки без ограничения.")
        elif remaining > 0:
            self.hint.setText(f"Можно пройти ещё раз · осталось попыток: {remaining}")
        else:
            self.hint.setText("Лимит попыток исчерпан.")

        self.retry_btn.setEnabled(remaining is None or remaining > 0)
