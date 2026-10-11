"""Вкладка «Сценарии»: список сценариев теста, настройка и выгрузка пакета."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from quiz_admin import services
from quiz_admin.config import get_exports_dir
from quiz_admin.models import Quiz
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.dialogs import ask_yes_no, show_errors
from quiz_admin.ui.scenario_dialog import ScenarioDialog
from quiz_admin.validation import PackageValidationError


class ScenariosTab(QWidget):
    def __init__(self, storage: AdminStorage, quiz: Quiz, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._storage = storage
        self._quiz = quiz

        layout = QVBoxLayout(self)
        hint = QLabel(
            "Сценарий задаёт, как воспроизводить вопросы теста: время, попытки, перемешивание, "
            "пороги оценок. Выгружаемый пакет = тест + один сценарий; его загружают в плеер."
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.list = QListWidget()
        layout.addWidget(self.list, stretch=1)

        row = QHBoxLayout()
        self.new_btn = QPushButton("+ Сценарий")
        self.edit_btn = QPushButton("Настроить…")
        self.copy_btn = QPushButton("Копировать")
        self.del_btn = QPushButton("Удалить")
        self.del_btn.setObjectName("danger")
        self.export_btn = QPushButton("Выгрузить пакет для плеера…")
        self.export_btn.setObjectName("primary")
        for b in (self.new_btn, self.edit_btn, self.copy_btn, self.del_btn):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.export_btn)
        layout.addLayout(row)

        self.new_btn.clicked.connect(self._new)
        self.edit_btn.clicked.connect(self._edit)
        self.copy_btn.clicked.connect(self._copy)
        self.del_btn.clicked.connect(self._delete)
        self.export_btn.clicked.connect(self._export)
        self.list.itemDoubleClicked.connect(lambda _i: self._edit())
        self.list.currentRowChanged.connect(lambda _r: self._update_buttons())
        self.reload()

    def reload(self) -> None:
        current = self._current_id()
        self.list.clear()
        for s in self._storage.list_scenarios(self._quiz.id):
            attempts = "∞" if s.attempts_unlimited else str(s.allowed_attempts)
            time_text = (
                "авто" if s.time_limit_mode == "auto" else f"{s.time_limit_minutes} мин"
            )
            item = QListWidgetItem(
                f"{s.name}\nвремя: {time_text} · попыток: {attempts} · "
                f"оценки от {s.grade_3_min_percent}/{s.grade_4_min_percent}/{s.grade_5_min_percent} %"
            )
            item.setData(Qt.ItemDataRole.UserRole, s.id)
            self.list.addItem(item)
            if s.id == current:
                self.list.setCurrentItem(item)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)
        self._update_buttons()

    def _current_id(self) -> int | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_buttons(self) -> None:
        has = self._current_id() is not None
        for b in (self.edit_btn, self.copy_btn, self.del_btn, self.export_btn):
            b.setEnabled(has)

    def _new(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Новый сценарий", "Название сценария:", text="Основной"
        )
        if not ok or not name.strip():
            return
        scenario = self._storage.create_scenario(self._quiz.id, name)
        self.reload()
        if ScenarioDialog(self._storage, self._quiz, scenario, self).exec():
            self.reload()

    def _edit(self) -> None:
        scenario_id = self._current_id()
        scenario = self._storage.get_scenario(scenario_id) if scenario_id else None
        if scenario is None:
            return
        if ScenarioDialog(self._storage, self._quiz, scenario, self).exec():
            self.reload()

    def _copy(self) -> None:
        scenario_id = self._current_id()
        if scenario_id:
            services.duplicate_scenario(self._storage, scenario_id)
            self.reload()

    def _delete(self) -> None:
        scenario_id = self._current_id()
        if scenario_id and ask_yes_no(self, "Удаление", "Удалить выбранный сценарий?"):
            self._storage.delete_scenario(scenario_id)
            self.reload()

    def _export(self) -> None:
        scenario_id = self._current_id()
        scenario = self._storage.get_scenario(scenario_id) if scenario_id else None
        if scenario is None:
            return
        try:
            services.build_package(self._storage, scenario.id)
        except PackageValidationError as exc:
            show_errors(self, "Пакет нельзя выгрузить", exc.errors)
            return
        default = Path(get_exports_dir()) / services.suggested_filename(self._quiz, scenario)
        path, _ = QFileDialog.getSaveFileName(
            self, "Выгрузить пакет для плеера", str(default), "JSON (*.json)"
        )
        if not path:
            return
        try:
            services.export_package(self._storage, scenario.id, Path(path))
        except OSError as exc:
            show_errors(self, "Не удалось записать файл", [str(exc)])
            return
        QMessageBox.information(
            self, "Готово", f"Пакет сохранён:\n{path}\n\nЗагрузите его в плеере через «+ Добавить комнату»."
        )
