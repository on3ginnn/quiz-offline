"""Панель вопросов: список слева, редактор вопроса справа, общее сохранение."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from quiz_admin import services
from quiz_admin.models import (
    QUESTION_MULTIPLE,
    QUESTION_SINGLE,
    OptionDraft,
    QuestionDraft,
)
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.dialogs import ask_save_changes, show_errors
from quiz_admin.ui.responsive_splitter import ResponsiveSplitter
from quiz_admin.ui.rich_list import RichListWidget, add_rich_item, update_rich_item
from quiz_admin.validation import PackageValidationError, validate_question


class _AutoHeightEdit(QPlainTextEdit):
    """Многострочное поле, растущее по содержимому (до 6 строк): длинный вариант виден целиком."""

    MAX_LINES = 6

    def __init__(self, text: str = "") -> None:
        super().__init__()
        self.setPlainText(text)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._fit)

    def text(self) -> str:
        return self.toPlainText()

    def _fit(self) -> None:
        lines = max(1, min(self.MAX_LINES, round(self.document().size().height())))
        extra = max(self.height() - self.viewport().height(), 18)
        margin = int(self.document().documentMargin() * 2)
        self.setFixedHeight(lines * self.fontMetrics().lineSpacing() + margin + extra)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._fit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if event.oldSize().width() != event.size().width():
            self._fit()


class _OptionRow(QWidget):
    toggled = pyqtSignal(object, bool)
    edited = pyqtSignal()
    remove_requested = pyqtSignal(object)

    def __init__(self, option: OptionDraft) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        self.correct = QCheckBox("Верный")
        self.correct.setToolTip("Отметьте, если этот вариант — правильный ответ")
        self.correct.setChecked(option.is_correct)
        self.text = _AutoHeightEdit(option.text)
        self.text.setPlaceholderText("Текст варианта ответа")
        self.remove_btn = QToolButton()
        self.remove_btn.setObjectName("removeOption")
        self.remove_btn.setText("Удалить")
        self.remove_btn.setToolTip("Удалить этот вариант")
        row.addWidget(self.correct, alignment=Qt.AlignmentFlag.AlignTop)
        row.addWidget(self.text, stretch=1)
        row.addWidget(self.remove_btn, alignment=Qt.AlignmentFlag.AlignTop)
        self.correct.toggled.connect(lambda checked: self.toggled.emit(self, checked))
        self.text.textChanged.connect(self.edited.emit)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))


class QuestionEditor(QWidget):
    """Редактор одного вопроса; пишет изменения прямо в QuestionDraft."""

    edited = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._draft: QuestionDraft | None = None
        self._loading = False
        self._rows: list[_OptionRow] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self._section("Текст вопроса"))
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Введите вопрос…")
        self.text_edit.setMinimumHeight(110)
        layout.addWidget(self.text_edit)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Сколько ответов верных:"))
        self.type_combo = QComboBox()
        self.type_combo.addItem("Один верный ответ", QUESTION_SINGLE)
        self.type_combo.addItem("Несколько верных ответов", QUESTION_MULTIPLE)
        type_row.addWidget(self.type_combo)
        type_row.addStretch(1)
        layout.addLayout(type_row)

        layout.addWidget(self._section("Варианты ответа"))
        self.options_host = QVBoxLayout()
        self.options_host.setSpacing(10)
        layout.addLayout(self.options_host)
        self.add_option_btn = QPushButton("+ Добавить вариант")
        layout.addWidget(self.add_option_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.problems = QLabel()
        self.problems.setObjectName("warn")
        self.problems.setWordWrap(True)
        layout.addWidget(self.problems)
        layout.addStretch(1)

        self.text_edit.textChanged.connect(self._on_text)
        self.type_combo.currentIndexChanged.connect(self._on_type)
        self.add_option_btn.clicked.connect(self._add_option)
        self.set_question(None)

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def set_question(self, draft: QuestionDraft | None) -> None:
        self._draft = draft
        self._loading = True
        self.setEnabled(draft is not None)
        self.text_edit.setPlainText(draft.text if draft else "")
        index = self.type_combo.findData(draft.question_type if draft else QUESTION_SINGLE)
        self.type_combo.setCurrentIndex(max(0, index))
        self._rebuild_rows()
        self._loading = False
        self._refresh_problems()

    def _rebuild_rows(self) -> None:
        for row in self._rows:
            self.options_host.removeWidget(row)
            row.hide()
            row.deleteLater()
        self._rows = []
        if self._draft is None:
            return
        for option in self._draft.options:
            self._append_row(option)

    def _append_row(self, option: OptionDraft) -> None:
        row = _OptionRow(option)
        row.toggled.connect(self._on_correct_toggled)
        row.edited.connect(self._sync)
        row.remove_requested.connect(self._remove_option)
        self.options_host.addWidget(row)
        self._rows.append(row)

    def _add_option(self) -> None:
        if self._draft is None:
            return
        option = OptionDraft("", False)
        self._draft.options.append(option)
        self._append_row(option)
        self._rows[-1].text.setFocus()
        self._sync()

    def _remove_option(self, row: _OptionRow) -> None:
        if self._draft is None or row not in self._rows:
            return
        idx = self._rows.index(row)
        del self._draft.options[idx]
        self._rows.pop(idx)
        self.options_host.removeWidget(row)
        row.hide()
        row.deleteLater()
        self._sync()

    def _on_correct_toggled(self, row: _OptionRow, checked: bool) -> None:
        if self._loading:
            return
        if checked and self.type_combo.currentData() == QUESTION_SINGLE:
            self._loading = True
            for other in self._rows:
                if other is not row:
                    other.correct.setChecked(False)
            self._loading = False
        self._sync()

    def _on_text(self) -> None:
        if not self._loading:
            self._sync()

    def _on_type(self) -> None:
        if self._loading or self._draft is None:
            return
        if self.type_combo.currentData() == QUESTION_SINGLE:
            seen = False
            self._loading = True
            for row in self._rows:
                if row.correct.isChecked():
                    if seen:
                        row.correct.setChecked(False)
                    seen = True
            self._loading = False
        self._sync()

    def _sync(self) -> None:
        """Перенести состояние виджетов в черновик."""
        if self._draft is None or self._loading:
            return
        self._draft.text = self.text_edit.toPlainText()
        self._draft.question_type = self.type_combo.currentData()
        for option, row in zip(self._draft.options, self._rows):
            option.text = row.text.text()
            option.is_correct = row.correct.isChecked()
        self._refresh_problems()
        self.edited.emit()

    def _refresh_problems(self) -> None:
        errors = validate_question(self._draft, "") if self._draft else []
        self.problems.setText("\n".join(e.lstrip(": ") for e in errors))


class QuestionsPanel(QWidget):
    """Банк вопросов теста или темы с общим сохранением."""

    saved = pyqtSignal()

    def __init__(
        self,
        storage: AdminStorage,
        quiz_id: int,
        topic_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._storage = storage
        self._quiz_id = quiz_id
        self._topic_id = topic_id
        self._drafts: list[QuestionDraft] = []
        self._dirty = False
        self._current = -1

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        splitter = ResponsiveSplitter(narrow_lines=40, vertical_min_lines=[16, 24])
        root.addWidget(splitter)

        left_host = QWidget()
        left = QVBoxLayout(left_host)
        left.setContentsMargins(0, 0, 8, 0)
        left.setSpacing(10)
        self.count_label = QLabel()
        self.count_label.setObjectName("sectionTitle")
        left.addWidget(self.count_label)
        self.list = RichListWidget()
        left.addWidget(self.list, stretch=1)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.add_btn = QPushButton("+ Добавить вопрос")
        self.up_btn = QPushButton("↑ Выше")
        self.down_btn = QPushButton("↓ Ниже")
        self.del_btn = QPushButton("Удалить")
        self.del_btn.setObjectName("danger")
        left.addWidget(self.add_btn)
        for b in (self.up_btn, self.down_btn):
            buttons.addWidget(b)
        left.addLayout(buttons)
        left.addWidget(self.del_btn)
        self.save_btn = QPushButton("Сохранить вопросы")
        self.save_btn.setObjectName("primary")
        left.addWidget(self.save_btn)
        self.save_state = QLabel()
        self.save_state.setObjectName("hint")
        self.save_state.setWordWrap(True)
        left.addWidget(self.save_state)
        left_host.setMinimumWidth(300)
        splitter.addWidget(left_host)

        self.editor = QuestionEditor()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.editor)
        scroll.setMinimumWidth(360)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self.list.currentRowChanged.connect(self._on_row)
        self.add_btn.clicked.connect(self._add)
        self.del_btn.clicked.connect(self._delete)
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn.clicked.connect(lambda: self._move(1))
        self.save_btn.clicked.connect(self.save)
        self.editor.edited.connect(self._on_edited)
        self.load()

    # --- состояние -------------------------------------------------------

    def load(self) -> None:
        self._drafts = self._storage.list_questions(self._quiz_id, self._topic_id)
        self._dirty = False
        self._refresh_list(0 if self._drafts else -1)
        self._update_buttons()

    def has_unsaved(self) -> bool:
        return self._dirty

    def confirm_leave(self) -> bool:
        """Спросить про несохранённое; True — можно уходить."""
        if not self._dirty:
            return True
        choice = ask_save_changes(self)
        if choice == "save":
            return self.save()
        return choice == "discard"

    def save(self) -> bool:
        try:
            services.save_questions(
                self._storage, self._quiz_id, self._topic_id, self._drafts
            )
        except PackageValidationError as exc:
            show_errors(self, "Не удалось сохранить вопросы", exc.errors)
            return False
        self._dirty = False
        self.load()
        self.saved.emit()
        return True

    # --- список ----------------------------------------------------------

    def _row_texts(self, idx: int, q: QuestionDraft) -> tuple[str, str, bool]:
        text = " ".join((q.text or "").split()) or "(пустой вопрос)"
        if len(text) > 140:
            text = text[:137] + "…"
        invalid = bool(validate_question(q))
        kind = "несколько верных" if q.question_type == QUESTION_MULTIPLE else "один верный"
        details = f"{kind} · вариантов: {len(q.options)}"
        if invalid:
            details += " · требует доработки"
        return f"{idx}. {text}", details, invalid

    def _refresh_list(self, select: int) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for i, q in enumerate(self._drafts, start=1):
            title, details, invalid = self._row_texts(i, q)
            add_rich_item(self.list, title, details, warn=invalid)
        self.list.blockSignals(False)
        self._refresh_count()
        if select >= 0 and self._drafts:
            select = min(select, len(self._drafts) - 1)
            self.list.setCurrentRow(select)
            self._current = select
            self.editor.set_question(self._drafts[select])
        else:
            self._current = -1
            self.editor.set_question(None)
        self._update_buttons()

    def _refresh_count(self) -> None:
        self.count_label.setText(f"Вопросов: {len(self._drafts)}")

    def _on_row(self, row: int) -> None:
        self._current = row
        self.editor.set_question(self._drafts[row] if 0 <= row < len(self._drafts) else None)
        self._update_buttons()

    def _on_edited(self) -> None:
        self._dirty = True
        if 0 <= self._current < len(self._drafts):
            item = self.list.item(self._current)
            if item is not None:
                title, details, invalid = self._row_texts(
                    self._current + 1, self._drafts[self._current]
                )
                update_rich_item(item, title, details, warn=invalid)
                self.list.scheduleDelayedItemsLayout()
        self._update_buttons()

    def _add(self) -> None:
        self._drafts.append(
            QuestionDraft("", QUESTION_SINGLE, [OptionDraft("", True), OptionDraft("", False)])
        )
        self._dirty = True
        self._refresh_list(len(self._drafts) - 1)
        self.editor.text_edit.setFocus()

    def _delete(self) -> None:
        if not 0 <= self._current < len(self._drafts):
            return
        del self._drafts[self._current]
        self._dirty = True
        self._refresh_list(self._current)

    def _move(self, delta: int) -> None:
        i, j = self._current, self._current + delta
        if not (0 <= i < len(self._drafts) and 0 <= j < len(self._drafts)):
            return
        self._drafts[i], self._drafts[j] = self._drafts[j], self._drafts[i]
        self._dirty = True
        self._refresh_list(j)

    def _update_buttons(self) -> None:
        has = 0 <= self._current < len(self._drafts)
        self.del_btn.setEnabled(has)
        self.up_btn.setEnabled(has and self._current > 0)
        self.down_btn.setEnabled(has and self._current < len(self._drafts) - 1)
        self.save_btn.setEnabled(self._dirty)
        self.save_btn.setText("Сохранить вопросы" if self._dirty else "Всё сохранено")
        self.save_state.setText(
            "Есть несохранённые изменения — нажмите «Сохранить вопросы»."
            if self._dirty
            else ""
        )
