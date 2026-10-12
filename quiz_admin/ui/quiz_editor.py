"""Экран редактирования теста: вкладки вопросов/тем и сценариев."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from quiz_admin.models import QUIZ_COMPOSITE
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.questions_panel import QuestionsPanel
from quiz_admin.ui.scenarios_tab import ScenariosTab
from quiz_admin.ui.topics_tab import TopicsTab


class QuizEditorWidget(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, storage: AdminStorage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._storage = storage
        self._quiz_id: int | None = None
        self._content: QuestionsPanel | TopicsTab | None = None
        self._scenarios: ScenariosTab | None = None
        self._tab_index = 0

        # Вся страница прокручивается: при крупном тексте панели не сжимаются
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 8, 0)
        root.setSpacing(12)
        top = QHBoxLayout()
        self.back_btn = QPushButton("← К списку тестов")
        self.back_btn.setObjectName("back")
        self.rename_btn = QPushButton("Переименовать тест")
        top.addWidget(self.back_btn)
        top.addStretch(1)
        top.addWidget(self.rename_btn)
        root.addLayout(top)
        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.title_label.setWordWrap(True)
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitle")
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        self.back_btn.clicked.connect(self._go_back)
        self.rename_btn.clicked.connect(self._rename)
        self.tabs.currentChanged.connect(self._on_tab)

    def open_quiz(self, quiz_id: int) -> None:
        self._quiz_id = quiz_id
        quiz = self._storage.get_quiz(quiz_id)
        if quiz is None:
            self.back_requested.emit()
            return
        composite = quiz.kind == QUIZ_COMPOSITE
        self.title_label.setText(quiz.title)
        self.subtitle_label.setText(
            "Мультитест: вопросы лежат в темах. Для каждой темы можно задать квоту в сценарии." if composite else "Обычный тест: один список вопросов."
        )
        self.tabs.blockSignals(True)
        while self.tabs.count():
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            widget.deleteLater()
        if composite:
            self._content = TopicsTab(self._storage, quiz)
            self.tabs.addTab(self._content, "Темы и вопросы")
        else:
            self._content = QuestionsPanel(self._storage, quiz.id)
            self.tabs.addTab(self._content, "Вопросы")
        self._scenarios = ScenariosTab(self._storage, quiz)
        self.tabs.addTab(self._scenarios, "Сценарии прохождения")
        self.tabs.setCurrentIndex(0)
        self._tab_index = 0
        self.tabs.blockSignals(False)

    def _confirm_leave_content(self) -> bool:
        return self._content is None or self._content.confirm_leave()

    def _on_tab(self, index: int) -> None:
        if self._tab_index == 0 and index != 0 and not self._confirm_leave_content():
            self.tabs.blockSignals(True)
            self.tabs.setCurrentIndex(0)
            self.tabs.blockSignals(False)
            return
        self._tab_index = index
        if index == 1 and self._scenarios is not None:
            self._scenarios.reload()

    def _go_back(self) -> None:
        if self._confirm_leave_content():
            self.back_requested.emit()

    def _rename(self) -> None:
        if self._quiz_id is None:
            return
        quiz = self._storage.get_quiz(self._quiz_id)
        if quiz is None:
            return
        title, ok = QInputDialog.getText(
            self, "Переименовать тест", "Название теста:", text=quiz.title
        )
        if ok and title.strip():
            self._storage.rename_quiz(quiz.id, title)
            self.title_label.setText(title.strip())
