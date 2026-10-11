import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from quiz_admin import services
from quiz_admin.models import OptionDraft, QuestionDraft
from quiz_admin.storage import AdminStorage
from quiz_admin.ui.main_window import MainWindow
from quiz_admin.ui.questions_panel import QuestionsPanel
from quiz_admin.ui.scenario_dialog import ScenarioDialog
from quiz_admin.ui.theme import app_stylesheet


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(app_stylesheet())
    return app


@pytest.fixture
def storage(tmp_path):
    s = AdminStorage(tmp_path / "admin.sqlite")
    yield s
    s.close()


def _fill(storage, title="Тест", n=2):
    quiz = storage.create_quiz(title, "single")
    qs = [
        QuestionDraft(f"Q{i}", "single", [OptionDraft("a", True), OptionDraft("b")])
        for i in range(n)
    ]
    services.save_questions(storage, quiz.id, None, qs)
    return quiz


def test_main_window_lists_quizzes_and_opens_editor(qapp, storage):
    quiz = _fill(storage)
    window = MainWindow(storage)
    assert window.library.list.count() == 1
    window.library.open_requested.emit(quiz.id)
    assert window.stack.currentWidget() is window.editor
    assert window.editor.tabs.count() == 2


def test_questions_panel_edit_and_save(qapp, storage, monkeypatch):
    shown = []
    monkeypatch.setattr(
        "quiz_admin.ui.questions_panel.show_errors", lambda *a: shown.append(a)
    )
    quiz = _fill(storage)
    panel = QuestionsPanel(storage, quiz.id)
    assert panel.list.count() == 2
    panel.editor.text_edit.setPlainText("Новый текст")
    assert panel.has_unsaved()
    assert panel.save()
    assert storage.list_questions(quiz.id)[0].text == "Новый текст"

    panel._add()
    assert panel.has_unsaved()
    assert not panel.save()  # пустой вопрос не проходит валидацию
    assert shown
    assert storage.count_questions(quiz.id) == 2


def test_single_type_keeps_one_correct_option(qapp, storage):
    quiz = _fill(storage)
    panel = QuestionsPanel(storage, quiz.id)
    rows = panel.editor._rows
    rows[1].correct.setChecked(True)
    assert [r.correct.isChecked() for r in rows] == [False, True]


def test_scenario_dialog_saves_policy_and_quotas(qapp, storage):
    a = _fill(storage, "A", 3)
    b = _fill(storage, "B", 2)
    composite = services.merge_quizzes(storage, "Сводный", [a.id, b.id])
    scenario = storage.create_scenario(composite.id, "S")
    topics = storage.list_topics(composite.id)

    dialog = ScenarioDialog(storage, composite, scenario)
    dialog.attempts_unlimited.setChecked(True)
    dialog.time_mode.setCurrentIndex(dialog.time_mode.findData("manual"))
    dialog.time_minutes.setValue(45)
    _topic, check, spin = dialog._quota_rows[0]
    check.setChecked(True)
    spin.setValue(2)
    dialog._accept()

    saved = storage.get_scenario(scenario.id)
    assert saved.attempts_unlimited and saved.allowed_attempts is None
    assert saved.time_limit_minutes == 45
    assert storage.get_quotas(scenario.id) == {topics[0].id: 2}
