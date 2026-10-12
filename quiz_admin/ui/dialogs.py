"""Мелкие диалоги и общие помощники."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from quiz_admin.models import QUIZ_COMPOSITE, QUIZ_SINGLE, QuizSummary
from quiz_admin.ui.rich_list import RichListWidget, add_rich_item


def show_errors(parent: QWidget | None, title: str, errors: list[str]) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(title)
    box.setInformativeText("\n".join(f"• {e}" for e in errors))
    box.addButton("Закрыть", QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def ask_yes_no(parent: QWidget | None, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    yes_btn = box.addButton("Да", QMessageBox.ButtonRole.YesRole)
    box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(yes_btn)
    box.exec()
    return box.clickedButton() == yes_btn


def ask_save_changes(parent: QWidget | None) -> str:
    """Вернуть "save" | "discard" | "cancel"."""
    box = QMessageBox(parent)
    box.setWindowTitle("Несохранённые изменения")
    box.setText("В вопросах есть несохранённые изменения.")
    box.setIcon(QMessageBox.Icon.Question)
    save_btn = box.addButton("Сохранить", QMessageBox.ButtonRole.AcceptRole)
    discard_btn = box.addButton("Не сохранять", QMessageBox.ButtonRole.DestructiveRole)
    box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(save_btn)
    box.exec()
    clicked = box.clickedButton()
    if clicked == save_btn:
        return "save"
    if clicked == discard_btn:
        return "discard"
    return "cancel"


class NewQuizDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новый тест")
        self.setMinimumWidth(520)
        form = QFormLayout()
        form.setVerticalSpacing(12)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Например: Сестринское дело")
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Обычный тест", QUIZ_SINGLE)
        self.kind_combo.addItem("Мультитест (несколько тем)", QUIZ_COMPOSITE)
        form.addRow("Название", self.title_edit)
        form.addRow("Вид", self.kind_combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Создать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if self.title_edit.text().strip():
            self.accept()

    def values(self) -> tuple[str, str]:
        return self.title_edit.text().strip(), self.kind_combo.currentData()


class PickQuizzesDialog(QDialog):
    """Выбор обычных тестов (для объединения или темы из теста)."""

    def __init__(
        self,
        summaries: list[QuizSummary],
        *,
        title: str,
        hint: str,
        multi: bool,
        ask_title: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        self.title_edit: QLineEdit | None = None
        if ask_title:
            self.title_edit = QLineEdit()
            self.title_edit.setPlaceholderText("Название мультитеста")
            layout.addWidget(self.title_edit)
        self.list = RichListWidget()
        if multi:
            self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for s in summaries:
            item = add_rich_item(
                self.list, s.quiz.title, f"вопросов: {s.question_count}", data=s.quiz.id
            )
            if multi:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
        layout.addWidget(self.list, stretch=1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Готово")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._multi = multi

    def _accept(self) -> None:
        if self.title_edit is not None and not self.title_edit.text().strip():
            return
        if not self.selected_ids():
            return
        self.accept()

    def selected_ids(self) -> list[int]:
        ids: list[int] = []
        if self._multi:
            for i in range(self.list.count()):
                item = self.list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    ids.append(item.data(Qt.ItemDataRole.UserRole))
        elif self.list.currentItem() is not None:
            ids.append(self.list.currentItem().data(Qt.ItemDataRole.UserRole))
        return ids

    def chosen_title(self) -> str:
        return self.title_edit.text().strip() if self.title_edit else ""
