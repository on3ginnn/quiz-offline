"""Главный экран: библиотека тестов."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_admin import services
from quiz_admin.importers import ImportDataError, load_import_file
from quiz_admin.models import QUIZ_COMPOSITE, QUIZ_SINGLE
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.dialogs import (
    NewQuizDialog,
    PickQuizzesDialog,
    ask_yes_no,
    show_errors,
)


class LibraryWidget(QWidget):
    open_requested = pyqtSignal(int)

    def __init__(self, storage: AdminStorage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._storage = storage

        root = QVBoxLayout(self)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Конструктор тестов")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Тест содержит вопросы; сценарий прохождения задаёт правила. "
            "Пакет «тест + сценарий» выгружается для плеера."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles, stretch=1)
        self.new_btn = QPushButton("+ Новый тест")
        self.new_btn.setObjectName("primary")
        self.import_btn = QPushButton("Импорт JSON…")
        self.merge_btn = QPushButton("Объединить в мультитест…")
        for b in (self.import_btn, self.merge_btn, self.new_btn):
            header.addWidget(b)
        root.addLayout(header)

        self.empty_label = QLabel("Тестов пока нет. Создайте новый или импортируйте JSON.")
        self.empty_label.setObjectName("subtitle")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.empty_label)
        self.list = QListWidget()
        root.addWidget(self.list, stretch=1)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("Открыть")
        self.copy_btn = QPushButton("Дублировать")
        self.rename_btn = QPushButton("Переименовать")
        self.del_btn = QPushButton("Удалить")
        self.del_btn.setObjectName("danger")
        for b in (self.open_btn, self.copy_btn, self.rename_btn, self.del_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        root.addLayout(actions)

        self.new_btn.clicked.connect(self._new)
        self.import_btn.clicked.connect(self._import)
        self.merge_btn.clicked.connect(self._merge)
        self.open_btn.clicked.connect(self._open)
        self.copy_btn.clicked.connect(self._copy)
        self.rename_btn.clicked.connect(self._rename)
        self.del_btn.clicked.connect(self._delete)
        self.list.itemDoubleClicked.connect(lambda _i: self._open())
        self.list.currentRowChanged.connect(lambda _r: self._update_buttons())
        self.reload()

    def reload(self, select_id: int | None = None) -> None:
        summaries = self._storage.list_quizzes()
        self.list.clear()
        for s in summaries:
            if s.quiz.kind == QUIZ_COMPOSITE:
                meta = f"Мультитест · тем: {s.topic_count} · вопросов: {s.question_count}"
            else:
                meta = f"Тест · вопросов: {s.question_count}"
            item = QListWidgetItem(f"{s.quiz.title}\n{meta} · сценариев: {s.scenario_count}")
            item.setData(Qt.ItemDataRole.UserRole, s.quiz.id)
            self.list.addItem(item)
            if s.quiz.id == select_id:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self.empty_label.setVisible(not summaries)
        self.list.setVisible(bool(summaries))
        self.merge_btn.setEnabled(
            sum(1 for s in summaries if s.quiz.kind == QUIZ_SINGLE and s.question_count) >= 2
        )
        self._update_buttons()

    def _current_id(self) -> int | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_buttons(self) -> None:
        has = self._current_id() is not None
        for b in (self.open_btn, self.copy_btn, self.rename_btn, self.del_btn):
            b.setEnabled(has)

    # --- действия --------------------------------------------------------

    def _new(self) -> None:
        dialog = NewQuizDialog(self)
        if dialog.exec():
            title, kind = dialog.values()
            quiz = self._storage.create_quiz(title, kind)
            self.reload(quiz.id)
            self.open_requested.emit(quiz.id)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт теста", "", "JSON (*.json);;Все файлы (*)"
        )
        if not path:
            return
        try:
            imported = load_import_file(Path(path))
            quiz = services.import_quiz(self._storage, imported)
        except ImportDataError as exc:
            show_errors(self, "Файл нельзя импортировать", exc.errors)
            return
        self.reload(quiz.id)

    def _merge(self) -> None:
        sources = [
            s
            for s in self._storage.list_quizzes()
            if s.quiz.kind == QUIZ_SINGLE and s.question_count > 0
        ]
        dialog = PickQuizzesDialog(
            sources,
            title="Объединить в мультитест",
            hint="Отметьте тесты (минимум два): каждый станет темой нового мультитеста.",
            multi=True,
            ask_title=True,
            parent=self,
        )
        if not dialog.exec():
            return
        ids = dialog.selected_ids()
        if len(ids) < 2:
            show_errors(self, "Объединение", ["Выберите минимум два теста."])
            return
        quiz = services.merge_quizzes(self._storage, dialog.chosen_title(), ids)
        self.reload(quiz.id)

    def _open(self) -> None:
        quiz_id = self._current_id()
        if quiz_id is not None:
            self.open_requested.emit(quiz_id)

    def _copy(self) -> None:
        quiz_id = self._current_id()
        if quiz_id is not None:
            self.reload(services.duplicate_quiz(self._storage, quiz_id).id)

    def _rename(self) -> None:
        quiz = self._storage.get_quiz(self._current_id() or 0)
        if quiz is None:
            return
        title, ok = QInputDialog.getText(
            self, "Переименовать тест", "Название теста:", text=quiz.title
        )
        if ok and title.strip():
            self._storage.rename_quiz(quiz.id, title)
            self.reload(quiz.id)

    def _delete(self) -> None:
        quiz = self._storage.get_quiz(self._current_id() or 0)
        if quiz and ask_yes_no(
            self, "Удаление", f"Удалить «{quiz.title}» вместе с вопросами и сценариями?"
        ):
            self._storage.delete_quiz(quiz.id)
            self.reload()
