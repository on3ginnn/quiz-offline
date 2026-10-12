"""Диалог старта попытки: ФИО тремя полями."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from quiz_offline.models import RoomPackage
from quiz_offline.room_loader import normalize_full_name
from quiz_offline.selection import effective_time_limit_minutes


def compose_full_name(last: str, first: str, middle: str) -> str:
    """Собирает отображаемое ФИО из частей."""
    parts = [p.strip() for p in (last, first, middle) if p and p.strip()]
    return " ".join(parts)


class StartAttemptDialog(QDialog):
    def __init__(self, package: RoomPackage, parent=None) -> None:
        super().__init__(parent)
        self._package = package
        self.setWindowTitle("Начать попытку")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        room = package.room
        assert room is not None

        title = QLabel("Введите ваши данные")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        attempts = "без ограничения" if room.attempts_unlimited else room.allowed_attempts
        info = QLabel(
            f"Попыток: {attempts}\n"
            f"Для оценки «3» нужно набрать {room.grade_3_min_percent}%, "
            f"«4» — {room.grade_4_min_percent}%, "
            f"«5» — {room.grade_5_min_percent}%"
        )
        info.setObjectName("subtitle")
        info.setWordWrap(True)
        layout.addWidget(info)

        est_q = max(1, len(package.questions))
        mins = effective_time_limit_minutes(room, est_q)
        time_label = QLabel(
            f"Время на тест: {mins} мин"
        )
        time_label.setObjectName("subtitle")
        layout.addWidget(time_label)

        hint = QLabel(
            "Пишите ФИО одинаково при каждой попытке — по нему ведётся журнал."
        )
        hint.setWordWrap(True)
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        form = QFormLayout()
        self.last_edit = QLineEdit()
        self.last_edit.setPlaceholderText("Например: Иванов")
        form.addRow("Фамилия", self.last_edit)
        self.first_edit = QLineEdit()
        self.first_edit.setPlaceholderText("Например: Иван")
        form.addRow("Имя", self.first_edit)
        self.middle_edit = QLineEdit()
        self.middle_edit.setPlaceholderText("Необязательно")
        form.addRow("Отчество", self.middle_edit)
        form.setVerticalSpacing(10)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Начать тест")
        ok_btn.setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.last_edit.text().strip() or not self.first_edit.text().strip():
            QMessageBox.warning(
                self,
                "ФИО",
                "Укажите фамилию и имя.",
            )
            return
        display = compose_full_name(
            self.last_edit.text(),
            self.first_edit.text(),
            self.middle_edit.text(),
        )
        if not normalize_full_name(display):
            QMessageBox.warning(self, "ФИО", "Укажите фамилию и имя.")
            return
        self.accept()

    def full_name(self) -> str:
        return compose_full_name(
            self.last_edit.text(),
            self.first_edit.text(),
            self.middle_edit.text(),
        )
