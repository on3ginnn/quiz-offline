"""Вкладка «Темы» мультитеста: список тем слева, вопросы выбранной темы справа."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_admin import services
from quiz_admin.models import QUIZ_SINGLE, Quiz
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.dialogs import PickQuizzesDialog, ask_yes_no, show_errors
from quiz_admin.ui.questions_panel import QuestionsPanel
from quiz_admin.ui.responsive_splitter import ResponsiveSplitter
from quiz_admin.ui.rich_list import RichListWidget, add_rich_item, update_rich_item


class TopicsTab(QWidget):
    def __init__(self, storage: AdminStorage, quiz: Quiz, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._storage = storage
        self._quiz = quiz
        self._panel: QuestionsPanel | None = None
        self._topic_id: int | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        splitter = ResponsiveSplitter(narrow_lines=58, vertical_min_lines=[14, 40])
        root.addWidget(splitter)

        left_host = QWidget()
        left = QVBoxLayout(left_host)
        left.setContentsMargins(0, 0, 8, 0)
        left.setSpacing(10)
        title = QLabel("Темы")
        title.setObjectName("sectionTitle")
        left.addWidget(title)
        self.list = RichListWidget()
        left.addWidget(self.list, stretch=1)
        self.add_btn = QPushButton("+ Новая тема")
        self.from_btn = QPushButton("+ Тема из теста…")
        self.rename_btn = QPushButton("Переименовать")
        self.up_btn = QPushButton("↑ Выше")
        self.down_btn = QPushButton("↓ Ниже")
        self.del_btn = QPushButton("Удалить тему")
        self.del_btn.setObjectName("danger")
        left.addWidget(self.add_btn)
        left.addWidget(self.from_btn)
        arrows = QHBoxLayout()
        arrows.setSpacing(8)
        arrows.addWidget(self.up_btn)
        arrows.addWidget(self.down_btn)
        left.addLayout(arrows)
        left.addWidget(self.rename_btn)
        left.addWidget(self.del_btn)
        left_host.setMinimumWidth(230)
        splitter.addWidget(left_host)

        right_host = QWidget()
        self.panel_host = QVBoxLayout(right_host)
        self.panel_host.setContentsMargins(8, 0, 0, 0)
        self.placeholder = QLabel("Добавьте тему, чтобы редактировать её вопросы.")
        self.placeholder.setObjectName("subtitle")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.panel_host.addWidget(self.placeholder)
        splitter.addWidget(right_host)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([260, 900])

        self.add_btn.clicked.connect(self._add)
        self.from_btn.clicked.connect(self._add_from_quiz)
        self.rename_btn.clicked.connect(self._rename)
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn.clicked.connect(lambda: self._move(1))
        self.del_btn.clicked.connect(self._delete)
        self.list.currentRowChanged.connect(self._on_row)
        self._reload_list(select_id=None)

    # --- служебное -------------------------------------------------------

    def confirm_leave(self) -> bool:
        return self._panel is None or self._panel.confirm_leave()

    def _reload_list(self, select_id: int | None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        target_row = -1
        for row, topic in enumerate(self._storage.list_topics(self._quiz.id)):
            count = self._storage.count_questions(self._quiz.id, topic.id)
            add_rich_item(
                self.list,
                f"{topic.topic_order}. {topic.title}",
                f"вопросов: {count}",
                data=topic.id,
            )
            if topic.id == select_id:
                target_row = row
        if target_row < 0 and self.list.count():
            target_row = 0
        self.list.setCurrentRow(target_row)
        self.list.blockSignals(False)
        self._show_panel(self._current_id())
        self._update_buttons()

    def _current_id(self) -> int | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_panel(self, topic_id: int | None) -> None:
        if self._panel is not None:
            self.panel_host.removeWidget(self._panel)
            self._panel.deleteLater()
            self._panel = None
        self._topic_id = topic_id
        self.placeholder.setVisible(topic_id is None)
        if topic_id is not None:
            self._panel = QuestionsPanel(self._storage, self._quiz.id, topic_id)
            self._panel.saved.connect(self._refresh_counts)
            self.panel_host.addWidget(self._panel)

    def _refresh_counts(self) -> None:
        for row in range(self.list.count()):
            item = self.list.item(row)
            topic = self._storage.get_topic(item.data(Qt.ItemDataRole.UserRole))
            if topic:
                count = self._storage.count_questions(self._quiz.id, topic.id)
                update_rich_item(
                    item, f"{topic.topic_order}. {topic.title}", f"вопросов: {count}"
                )

    def _on_row(self, row: int) -> None:
        new_id = self._current_id()
        if new_id == self._topic_id:
            return
        if self._panel is not None and not self._panel.confirm_leave():
            self.list.blockSignals(True)
            for r in range(self.list.count()):
                if self.list.item(r).data(Qt.ItemDataRole.UserRole) == self._topic_id:
                    self.list.setCurrentRow(r)
            self.list.blockSignals(False)
            return
        self._show_panel(new_id)
        self._update_buttons()

    def _update_buttons(self) -> None:
        has = self._current_id() is not None
        row = self.list.currentRow()
        self.rename_btn.setEnabled(has)
        self.del_btn.setEnabled(has)
        self.up_btn.setEnabled(has and row > 0)
        self.down_btn.setEnabled(has and row < self.list.count() - 1)

    # --- действия --------------------------------------------------------

    def _add(self) -> None:
        if not self.confirm_leave():
            return
        title, ok = QInputDialog.getText(self, "Новая тема", "Название темы:")
        if ok and title.strip():
            topic = self._storage.add_topic(self._quiz.id, title)
            self._reload_list(select_id=topic.id)

    def _add_from_quiz(self) -> None:
        if not self.confirm_leave():
            return
        sources = [
            s
            for s in self._storage.list_quizzes()
            if s.quiz.kind == QUIZ_SINGLE and s.question_count > 0
        ]
        if not sources:
            show_errors(self, "Нет подходящих тестов", ["Нужен обычный тест с вопросами."])
            return
        dialog = PickQuizzesDialog(
            sources,
            title="Тема из теста",
            hint="Вопросы выбранного теста будут скопированы в новую тему.",
            multi=False,
            parent=self,
        )
        if dialog.exec():
            topic_id = services.add_topic_from_quiz(
                self._storage, self._quiz.id, dialog.selected_ids()[0]
            )
            self._reload_list(select_id=topic_id)

    def _rename(self) -> None:
        topic = self._storage.get_topic(self._current_id() or 0)
        if topic is None:
            return
        title, ok = QInputDialog.getText(
            self, "Переименовать тему", "Название темы:", text=topic.title
        )
        if ok and title.strip():
            self._storage.rename_topic(topic.id, title)
            self._refresh_counts()

    def _move(self, delta: int) -> None:
        topic_id = self._current_id()
        if topic_id is None or not self.confirm_leave():
            return
        self._storage.move_topic(topic_id, delta)
        self._reload_list(select_id=topic_id)

    def _delete(self) -> None:
        topic_id = self._current_id()
        if topic_id is None:
            return
        if ask_yes_no(self, "Удаление", "Удалить тему вместе с её вопросами?"):
            self._storage.delete_topic(topic_id)
            self._topic_id = None
            if self._panel is not None:
                self._panel.load()  # сбросить флаг несохранённого
            self._reload_list(select_id=None)
