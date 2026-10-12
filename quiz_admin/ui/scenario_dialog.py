"""Диалог настройки сценария прохождения и квот по темам."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from quiz_admin.models import Quiz, Scenario, Topic
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.dialogs import show_errors
from quiz_admin.validation import MAX_ATTEMPTS, validate_scenario


class ScenarioDialog(QDialog):
    def __init__(
        self,
        storage: AdminStorage,
        quiz: Quiz,
        scenario: Scenario,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._storage = storage
        self._scenario = scenario
        self._composite = quiz.kind == "composite"
        self._topics: list[Topic] = storage.list_topics(quiz.id) if self._composite else []
        self._pool = {
            t.id: storage.count_questions(quiz.id, t.id) for t in self._topics
        }
        self._bank_size = 0 if self._composite else storage.count_questions(quiz.id)
        self.setWindowTitle(f"Сценарий прохождения — {quiz.title}")
        self.setMinimumSize(660, 560)
        self.resize(760, 780)

        def card(title: str, hint: str = "") -> QFormLayout:
            frame = QFrame()
            frame.setObjectName("card")
            outer = QVBoxLayout(frame)
            outer.setContentsMargins(20, 16, 20, 18)
            outer.setSpacing(8)
            heading = QLabel(title)
            heading.setObjectName("sectionTitle")
            outer.addWidget(heading)
            if hint:
                sub = QLabel(hint)
                sub.setObjectName("subtitle")
                sub.setWordWrap(True)
                outer.addWidget(sub)
            form = QFormLayout()
            form.setVerticalSpacing(12)
            form.setHorizontalSpacing(16)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            outer.addLayout(form)
            sections.addWidget(frame)
            return form

        def note(text: str) -> QLabel:
            label = QLabel(text)
            label.setObjectName("hint")
            label.setWordWrap(True)
            return label

        content = QWidget()
        sections = QVBoxLayout(content)
        sections.setContentsMargins(0, 0, 8, 0)
        sections.setSpacing(14)

        main = card("Основное")
        self.name_edit = QLineEdit(scenario.name)
        main.addRow("Название сценария", self.name_edit)

        timing = card("Время и попытки")
        self.time_mode = QComboBox()
        self.time_mode.addItem("Авто — 1 минута на вопрос", "auto")
        self.time_mode.addItem("Задать вручную", "manual")
        self.time_minutes = QSpinBox()
        self.time_minutes.setRange(1, 600)
        self.time_minutes.setSuffix(" мин")
        time_row = QHBoxLayout()
        time_row.setSpacing(10)
        time_row.addWidget(self.time_mode, stretch=1)
        time_row.addWidget(self.time_minutes)
        timing.addRow("Время на тест", time_row)

        self.attempts_unlimited = QCheckBox("Без ограничения")
        self.attempts = QSpinBox()
        self.attempts.setRange(1, MAX_ATTEMPTS)
        attempts_row = QHBoxLayout()
        attempts_row.setSpacing(10)
        attempts_row.addWidget(self.attempts)
        attempts_row.addWidget(self.attempts_unlimited)
        attempts_row.addStretch(1)
        timing.addRow("Попыток на участника", attempts_row)

        questions = card("Вопросы")
        self.shuffle_questions = QCheckBox("Перемешивать порядок вопросов")
        self.shuffle_options = QCheckBox("Перемешивать варианты ответов")
        questions.addRow(self.shuffle_questions)
        questions.addRow(self.shuffle_options)

        self.selection_mode = QComboBox()
        self.selection_mode.addItem("Новая выборка при каждой попытке", "per_attempt")
        self.selection_mode.addItem("Одна выборка на участника", "per_participant")
        questions.addRow("Какие вопросы попадаются", self.selection_mode)
        questions.addRow(
            note("«Одна выборка» — участник при повторе получает те же вопросы.")
        )

        self.sample_all = QCheckBox("Все вопросы")
        self.sample = QSpinBox()
        self.sample.setRange(1, max(1, self._bank_size))
        sample_row_w = QWidget()
        sample_row = QHBoxLayout(sample_row_w)
        sample_row.setContentsMargins(0, 0, 0, 0)
        sample_row.setSpacing(10)
        sample_row.addWidget(self.sample)
        sample_row.addWidget(self.sample_all)
        sample_row.addStretch(1)
        self._sample_row_label = QLabel("Сколько вопросов в попытке")
        questions.addRow(self._sample_row_label, sample_row_w)
        self._sample_widgets = (self._sample_row_label, self.sample, self.sample_all, sample_row_w)

        results = card("Что видит участник после теста")
        self.show_results = QCheckBox("Показывать оценку и результат")
        self.show_answers = QCheckBox("Показывать его ответы")
        self.show_correct = QCheckBox("Показывать правильные ответы")
        results.addRow(self.show_results)
        results.addRow(self.show_answers)
        results.addRow(self.show_correct)

        grading = card(
            "Оценки",
            "Минимальный процент правильных ответов для каждой оценки.",
        )
        self.g3 = QSpinBox()
        self.g4 = QSpinBox()
        self.g5 = QSpinBox()
        for label, spin in (("Для оценки «3» — от", self.g3), ("Для оценки «4» — от", self.g4), ("Для оценки «5» — от", self.g5)):
            spin.setRange(0, 100)
            spin.setSuffix(" %")
            grading.addRow(label, spin)
        self.attempt_mode = QComboBox()
        self.attempt_mode.addItem("Лучшая попытка", "best")
        self.attempt_mode.addItem("Последняя попытка", "last")
        grading.addRow("Какая попытка идёт в журнал", self.attempt_mode)

        self.quota_table: QTableWidget | None = None
        if self._composite:
            quotas = card(
                "Квоты по темам",
                "Сколько вопросов брать из каждой темы. Без отметки — берутся все вопросы темы, "
                "0 — тема пропускается.",
            )
            self.quota_table = QTableWidget(len(self._topics), 3)
            self.quota_table.setHorizontalHeaderLabels(["Тема", "Вопросов", "Квота"])
            self.quota_table.verticalHeader().setVisible(False)
            self.quota_table.setWordWrap(True)
            self.quota_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            header = self.quota_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            self.quota_table.verticalHeader().setDefaultSectionSize(64)
            self.quota_table.setMinimumHeight(
                min(420, 64 * len(self._topics) + 56)
            )
            quotas.addRow(self.quota_table)
        sections.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(scroll, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        save_btn.setText("Сохранить")
        save_btn.setObjectName("primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.time_mode.currentIndexChanged.connect(self._sync_enabled)
        self.attempts_unlimited.toggled.connect(self._sync_enabled)
        self.sample_all.toggled.connect(self._sync_enabled)
        self._load(scenario)
        self._load_quotas()
        self._sync_enabled()

    # --- загрузка --------------------------------------------------------

    def _load(self, s: Scenario) -> None:
        self.time_mode.setCurrentIndex(self.time_mode.findData(s.time_limit_mode))
        self.time_minutes.setValue(int(s.time_limit_minutes or 30))
        self.attempts_unlimited.setChecked(s.attempts_unlimited)
        self.attempts.setValue(int(s.allowed_attempts or 1))
        self.shuffle_questions.setChecked(s.shuffle_questions)
        self.shuffle_options.setChecked(s.shuffle_options)
        self.selection_mode.setCurrentIndex(self.selection_mode.findData(s.selection_mode))
        self.sample_all.setChecked(s.questions_sample_size is None)
        self.sample.setValue(int(s.questions_sample_size or self._bank_size or 1))
        self.show_results.setChecked(s.show_results)
        self.show_answers.setChecked(s.show_answers)
        self.show_correct.setChecked(s.show_correct_answers)
        self.g3.setValue(s.grade_3_min_percent)
        self.g4.setValue(s.grade_4_min_percent)
        self.g5.setValue(s.grade_5_min_percent)
        self.attempt_mode.setCurrentIndex(self.attempt_mode.findData(s.grade_attempt_mode))

    def _load_quotas(self) -> None:
        if self.quota_table is None:
            return
        stored = self._storage.get_quotas(self._scenario.id)
        self._quota_rows: list[tuple[Topic, QTableWidgetItem, QSpinBox]] = []
        for row, topic in enumerate(self._topics):
            self.quota_table.setItem(row, 0, QTableWidgetItem(topic.title))
            self.quota_table.setItem(row, 1, QTableWidgetItem(str(self._pool[topic.id])))
            for col in (0, 1):
                self.quota_table.item(row, col).setFlags(Qt.ItemFlag.ItemIsEnabled)
            cell = QWidget()
            h = QHBoxLayout(cell)
            h.setContentsMargins(8, 0, 8, 0)
            h.setSpacing(8)
            check = QCheckBox()
            spin = QSpinBox()
            spin.setRange(0, max(0, self._pool[topic.id]))
            quota = stored.get(topic.id)
            check.setChecked(quota is not None)
            spin.setValue(quota if quota is not None else self._pool[topic.id])
            spin.setEnabled(quota is not None)
            check.toggled.connect(spin.setEnabled)
            h.addWidget(check)
            h.addWidget(spin)
            self.quota_table.setCellWidget(row, 2, cell)
            self._quota_rows.append((topic, check, spin))

    def _sync_enabled(self) -> None:
        self.time_minutes.setEnabled(self.time_mode.currentData() == "manual")
        self.attempts.setEnabled(not self.attempts_unlimited.isChecked())
        for w in self._sample_widgets:
            w.setVisible(not self._composite)
        self.sample.setEnabled(not self.sample_all.isChecked())

    # --- сохранение ------------------------------------------------------

    def _collect(self) -> Scenario:
        s = self._scenario
        s.name = self.name_edit.text().strip()
        s.time_limit_mode = self.time_mode.currentData()
        s.time_limit_minutes = (
            self.time_minutes.value() if s.time_limit_mode == "manual" else None
        )
        s.attempts_unlimited = self.attempts_unlimited.isChecked()
        s.allowed_attempts = None if s.attempts_unlimited else self.attempts.value()
        s.shuffle_questions = self.shuffle_questions.isChecked()
        s.shuffle_options = self.shuffle_options.isChecked()
        s.selection_mode = self.selection_mode.currentData()
        s.questions_sample_size = (
            None if self._composite or self.sample_all.isChecked() else self.sample.value()
        )
        s.show_results = self.show_results.isChecked()
        s.show_answers = self.show_answers.isChecked()
        s.show_correct_answers = self.show_correct.isChecked()
        s.grade_3_min_percent = self.g3.value()
        s.grade_4_min_percent = self.g4.value()
        s.grade_5_min_percent = self.g5.value()
        s.grade_attempt_mode = self.attempt_mode.currentData()
        return s

    def _accept(self) -> None:
        scenario = self._collect()
        errors = validate_scenario(scenario)
        if errors:
            show_errors(self, "Проверьте настройки сценария", errors)
            return
        self._storage.update_scenario(scenario)
        if self.quota_table is not None:
            self._storage.set_quotas(
                scenario.id,
                {
                    topic.id: spin.value()
                    for topic, check, spin in self._quota_rows
                    if check.isChecked()
                },
            )
        self.accept()
