"""Экран зала: журнал участников комнаты."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quiz_offline.room_loader import RoomPackageError
from quiz_offline.storage import Storage
from quiz_offline.ui.formatters import format_datetime_ru, format_duration_short
from quiz_offline.ui.page_header import PageHeader
from quiz_offline.ui.room_meta import build_room_meta_labels
from quiz_offline.ui.start_dialog import StartAttemptDialog

# № | ФИО | … — без сокращений в заголовках
_HALL_COLUMNS = [
    "№",
    "ФИО",
    "Попыток",
    "Дата",
    "Время",
    "Последняя (% / оценка)",
    "Лучшая (% / оценка)",
]


class HallWidget(QWidget):
    back_home = pyqtSignal()
    start_attempt = pyqtSignal(int, str)

    def __init__(self, storage: Storage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.storage = storage
        self._room_public_id: str | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.header = PageHeader(
            self,
            on_back=self.back_home.emit,
            back_tooltip="Вернуться к списку комнат",
            back_text="← К комнатам",
        )
        layout.addWidget(self.header)

        self.start_btn = QPushButton("Начать попытку")
        self.start_btn.setObjectName("cta")
        self.start_btn.clicked.connect(self._on_start)
        self.header.set_trailing(self.start_btn)

        self.table = QTableWidget(0, len(_HALL_COLUMNS))
        self.table.setHorizontalHeaderLabels(_HALL_COLUMNS)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        layout.addWidget(self.table, stretch=1)

        self.empty_label = QLabel(
            "Пока никто не проходил этот тест.\n"
            "Нажмите «Начать попытку», чтобы пройти его первым."
        )
        self.empty_label.setObjectName("subtitle")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        layout.addWidget(self.empty_label, stretch=1)

    def load_room(self, room_public_id: str) -> None:
        self._room_public_id = room_public_id
        try:
            package = self.storage.load_package_for_room(room_public_id)
        except RoomPackageError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            self.back_home.emit()
            return

        room = package.room
        assert room is not None
        self.header.set_title(f"{package.quiz_title} · {room.name}")
        self.header.set_subtitle("")
        self.header.set_meta_badges(build_room_meta_labels(package))

        rows = self.storage.list_hall_participants(room_public_id)
        self.table.setRowCount(len(rows))
        self.table.setVisible(bool(rows))
        self.empty_label.setVisible(not rows)
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(row.full_name_display))
            self.table.setItem(
                i, 2, QTableWidgetItem(str(row.attempt_count))
            )
            self.table.setItem(
                i,
                3,
                QTableWidgetItem(format_datetime_ru(row.last_finished_at)),
            )
            self.table.setItem(
                i,
                4,
                QTableWidgetItem(format_duration_short(row.last_duration_sec)),
            )
            last = (
                f"{row.last_weighted_percent or 0}% / {row.last_grade or 2}"
                if row.last_weighted_percent is not None
                else "—"
            )
            best = (
                f"{row.best_weighted_percent or 0}% / {row.best_grade or 2}"
                if row.best_weighted_percent is not None
                else "—"
            )
            self.table.setItem(i, 5, QTableWidgetItem(last))
            self.table.setItem(i, 6, QTableWidgetItem(best))

    def _on_start(self) -> None:
        if not self._room_public_id:
            return
        try:
            package = self.storage.load_package_for_room(self._room_public_id)
        except RoomPackageError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        room = package.room
        assert room is not None

        dlg = StartAttemptDialog(package, self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        full_name = dlg.full_name()
        try:
            participant_id = self.storage.get_or_create_participant(
                self._room_public_id, full_name
            )
        except ValueError as exc:
            QMessageBox.warning(self, "ФИО", str(exc))
            return

        used = self.storage.count_attempts(participant_id)
        cap = room.attempts_cap()
        if cap is not None and used >= cap:
            QMessageBox.warning(
                self,
                "Лимит попыток",
                f"Для «{full_name}» исчерпан лимит ({cap}).",
            )
            return

        self.start_attempt.emit(participant_id, full_name)
