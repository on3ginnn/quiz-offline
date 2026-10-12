"""Главный экран: библиотека тестов."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_admin import services
from quiz_admin.importers import ImportDataError, load_import_file
from quiz_admin.models import QUIZ_COMPOSITE, QUIZ_SINGLE
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.rich_list import RichListWidget, add_rich_item
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
        root.setSpacing(14)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Конструктор тестов")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Здесь хранятся тесты. Создайте тест, добавьте вопросы и настройте сценарий — "
            "затем выгрузите файл для программы прохождения."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles, stretch=1)
        root.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        self.new_btn = QPushButton("+ Новый тест")
        self.new_btn.setObjectName("primary")
        self.import_btn = QPushButton("Импорт из файла…")
        self.import_btn.setToolTip("Загрузить тест или пакет из JSON-файла")
        self.merge_btn = QPushButton("Объединить в мультитест…")
        self.merge_btn.setToolTip("Собрать из нескольких тестов один с темами (нужно ≥ 2 теста)")
        for b in (self.new_btn, self.import_btn, self.merge_btn):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        root.addLayout(toolbar)

        self.empty_label = QLabel(
            "Тестов пока нет.\nНажмите «+ Новый тест» или «Импорт из файла…»."
        )
        self.empty_label.setObjectName("emptyState")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.empty_label, stretch=1)
        self.list = RichListWidget()
        root.addWidget(self.list, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.open_btn = QPushButton("Открыть")
        self.open_btn.setObjectName("primary")
        self.copy_btn = QPushButton("Дублировать")
        self.rename_btn = QPushButton("Переименовать")
        self.del_btn = QPushButton("Удалить")
        self.del_btn.setObjectName("danger")
        for b in (self.open_btn, self.copy_btn, self.rename_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(self.del_btn)
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
            item = add_rich_item(
                self.list,
                s.quiz.title,
                f"{meta} · сценариев: {s.scenario_count}",
                data=s.quiz.id,
            )
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
