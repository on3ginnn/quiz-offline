"""Экран результатов попытки."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
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

        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        scroll.setWidget(host)
        page.addWidget(scroll)
        outer = QVBoxLayout(host)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)

        center = QHBoxLayout()
        center.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("resultCard")
        self.card.setMaximumWidth(760)
        card = QVBoxLayout(self.card)
        card.setContentsMargins(32, 28, 32, 24)
        card.setSpacing(16)

        self.grade_label = QLabel()
        self.grade_label.setObjectName("gradeResult")
        self.grade_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(self.grade_label)

        top_row = QHBoxLayout()
        top_row.setSpacing(24)

        # Оценка (5-балльная) + кольцо процентов — одна колонка
        grade_col = QVBoxLayout()
        grade_col.setSpacing(10)
        grade_col.setAlignment(Qt.AlignmentFlag.AlignHCenter)
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

        self.hint = QLabel()
        self.hint.setObjectName("subtitle")
        self.hint.setWordWrap(True)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(self.hint)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.setSpacing(10)
        self.leave_btn = QPushButton("Покинуть тест")
        self.leave_btn.setObjectName("resultBtn")
        self.leave_btn.setMinimumWidth(168)
        self.leave_btn.clicked.connect(self.leave_test.emit)
        self.retry_btn = QPushButton("Пройти ещё раз")
        self.retry_btn.setObjectName("primary")
        self.retry_btn.setMinimumWidth(168)
        self.retry_btn.clicked.connect(self.retry.emit)
        actions.addWidget(self.leave_btn)
        actions.addWidget(self.retry_btn)
        actions.addStretch(1)
        bottom_row.addLayout(actions, stretch=1)
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

        for widget in (self.card, self.grade_label, self.time_value_lbl):
            widget.setProperty("tone", visual.tone)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.grade_label.setText(f"Ваша оценка: {grade}")

        self.donut.set_value(
            result.weighted_percent,
            visual.color,
            center_text=f"{round(result.weighted_percent)}%",
        )
        self.percent_caption.setText(
            f"{format_grade_scale_caption(grade)} по 5-балльной шкале"
        )

        mins, secs = divmod(int(result.duration_sec), 60)
        self.time_value_lbl.setText(f"⏱  {mins}:{secs:02d}")

        if context.get("finished_by_timer"):
            self.hint.setText("Время истекло — ответы отправлены автоматически.")
        elif remaining is None:
            self.hint.setText("Попытки без ограничения.")
        elif remaining > 0:
            self.hint.setText(f"Можно пройти ещё раз · осталось попыток: {remaining}")
        else:
            self.hint.setText("Лимит попыток исчерпан.")

        self.retry_btn.setEnabled(remaining is None or remaining > 0)
