"""Главное окно конструктора: библиотека ↔ редактор теста."""

from __future__ import annotations

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from quiz_admin.storage import AdminStorage
from quiz_admin.ui.library_widget import LibraryWidget
from quiz_admin.ui.quiz_editor import QuizEditorWidget


class MainWindow(QMainWindow):
    def __init__(self, storage: AdminStorage) -> None:
        super().__init__()
        self.setWindowTitle("Quiz Admin — конструктор тестов")
        self.resize(1100, 740)
        self._storage = storage

        self.library = LibraryWidget(storage)
        self.editor = QuizEditorWidget(storage)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.library)
        self.stack.addWidget(self.editor)

        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.addWidget(self.stack)
        self.setCentralWidget(host)

        self.library.open_requested.connect(self._open_quiz)
        self.editor.back_requested.connect(self._go_library)

    def _open_quiz(self, quiz_id: int) -> None:
        self.editor.open_quiz(quiz_id)
        self.stack.setCurrentWidget(self.editor)

    def _go_library(self) -> None:
        self.library.reload(self.editor._quiz_id)
        self.stack.setCurrentWidget(self.library)
