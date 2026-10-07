"""Главное окно: Home → Hall → Taking → Results."""

from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from quiz_offline.storage import Storage
from quiz_offline.ui.hall_widget import HallWidget
from quiz_offline.ui.home_widget import HomeWidget
from quiz_offline.ui.results_widget import ResultsWidget
from quiz_offline.ui.taking_widget import TakingWidget


class MainWindow(QMainWindow):
    PAGE_HOME = 0
    PAGE_HALL = 1
    PAGE_TAKING = 2
    PAGE_RESULTS = 3

    def __init__(self, storage: Storage) -> None:
        super().__init__()
        self.storage = storage
        self.setWindowTitle("Quiz Offline")
        self.resize(960, 640)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.home = HomeWidget(storage)
        self.hall = HallWidget(storage)
        self.taking = TakingWidget(storage)
        self.results = ResultsWidget()

        self.stack.addWidget(self.home)
        self.stack.addWidget(self.hall)
        self.stack.addWidget(self.taking)
        self.stack.addWidget(self.results)

        self.home.open_room.connect(self._open_hall)
        self.home.rooms_changed.connect(self.home.refresh)
        self.hall.back_home.connect(self._go_home)
        self.hall.start_attempt.connect(self._start_attempt)
        self.taking.finished_attempt.connect(self._show_results)
        self.taking.cancelled.connect(self._open_hall_from_taking)
        self.results.leave_test.connect(self._open_hall_from_results)
        self.results.retry.connect(self._retry_attempt)

        self._current_room_id: str | None = None
        self._current_participant_id: int | None = None
        self._last_result_context: dict | None = None

        self._go_home()

    def _go_home(self) -> None:
        self._current_room_id = None
        self.home.refresh()
        self.stack.setCurrentIndex(self.PAGE_HOME)

    def _open_hall(self, room_public_id: str) -> None:
        self._current_room_id = room_public_id
        self.storage.touch_room_opened(room_public_id)
        self.hall.load_room(room_public_id)
        self.stack.setCurrentIndex(self.PAGE_HALL)

    def _open_hall_from_taking(self) -> None:
        if self._current_room_id:
            self._open_hall(self._current_room_id)

    def _open_hall_from_results(self) -> None:
        if self._current_room_id:
            self._open_hall(self._current_room_id)

    def _start_attempt(self, participant_id: int, full_name: str) -> None:
        if not self._current_room_id:
            return
        self._current_participant_id = participant_id
        self.taking.start_attempt(
            self._current_room_id,
            participant_id,
            full_name,
        )
        self.stack.setCurrentIndex(self.PAGE_TAKING)

    def _show_results(self, context: dict) -> None:
        self._last_result_context = context
        self.results.show_result(context)
        self.stack.setCurrentIndex(self.PAGE_RESULTS)

    def _retry_attempt(self) -> None:
        if self._last_result_context is None:
            return
        participant_id = self._last_result_context.get("participant_id")
        full_name = self._last_result_context.get("full_name", "")
        if participant_id and self._current_room_id:
            self._start_attempt(int(participant_id), str(full_name))
