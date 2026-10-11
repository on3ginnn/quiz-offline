import json

import pytest

from quiz_admin import services
from quiz_admin.importers import ImportDataError, parse_import
from quiz_admin.models import OptionDraft, QuestionDraft
from quiz_admin.storage import AdminStorage
from quiz_admin.validation import PackageValidationError, validate_question
from quiz_offline.room_loader import parse_room_package_dict


def _q(text: str, multiple: bool = False) -> QuestionDraft:
    if multiple:
        return QuestionDraft(
            text,
            "multiple",
            [OptionDraft("A", True), OptionDraft("B", True), OptionDraft("C", False)],
        )
    return QuestionDraft(text, "single", [OptionDraft("Да", True), OptionDraft("Нет")])


@pytest.fixture
def storage(tmp_path):
    s = AdminStorage(tmp_path / "admin.sqlite")
    yield s
    s.close()


def _single_quiz(storage, title="Анатомия", n=3):
    quiz = storage.create_quiz(title, "single")
    services.save_questions(storage, quiz.id, None, [_q(f"{title} {i}") for i in range(n)])
    return quiz


def test_question_validation_rules():
    assert validate_question(_q("ok")) == []
    assert validate_question(QuestionDraft("", "single", [OptionDraft("a", True)]))
    two_correct = QuestionDraft("x", "single", [OptionDraft("a", True), OptionDraft("b", True)])
    assert validate_question(two_correct)
    no_correct = QuestionDraft("x", "multiple", [OptionDraft("a"), OptionDraft("b")])
    assert validate_question(no_correct)


def test_save_questions_rejects_invalid(storage):
    quiz = storage.create_quiz("T", "single")
    with pytest.raises(PackageValidationError):
        services.save_questions(storage, quiz.id, None, [QuestionDraft("x", "single", [])])
    assert storage.count_questions(quiz.id) == 0


def test_single_package_roundtrips_through_player_loader(storage):
    quiz = _single_quiz(storage)
    services.save_questions(
        storage, quiz.id, None, storage.list_questions(quiz.id) + [_q("multi", True)]
    )
    scenario = storage.create_scenario(
        quiz.id, "Зачёт", time_limit_mode="manual", time_limit_minutes=20,
        allowed_attempts=2, grade_3_min_percent=0, grade_4_min_percent=50,
    )
    package = services.build_package(storage, scenario.id)
    parsed = parse_room_package_dict(json.loads(json.dumps(package, ensure_ascii=False)))
    assert parsed.quiz_kind == "single"
    assert len(parsed.questions) == 4
    assert parsed.room.name == "Зачёт"
    assert parsed.room.public_id == scenario.public_id
    assert parsed.room.time_limit_minutes == 20
    assert parsed.room.grade_3_min_percent == 0


def test_merge_and_composite_package_with_quotas(storage):
    a = _single_quiz(storage, "A", 3)
    b = _single_quiz(storage, "B", 2)
    composite = services.merge_quizzes(storage, "Сводный", [a.id, b.id])
    topics = storage.list_topics(composite.id)
    assert [t.title for t in topics] == ["A", "B"]
    assert [t.topic_order for t in topics] == [1, 2]
    assert storage.count_questions(composite.id, topics[0].id) == 3
    assert storage.count_questions(composite.id) == 0

    scenario = storage.create_scenario(composite.id, "Тренировка")
    storage.set_quotas(scenario.id, {topics[0].id: 2, topics[1].id: 1})
    package = services.build_package(storage, scenario.id)
    parsed = parse_room_package_dict(package)
    assert parsed.quiz_kind == "composite"
    assert {q.topic_order: q.question_count for q in parsed.topic_quotas} == {1: 2, 2: 1}
    assert parsed.room.questions_sample_size is None

    storage.set_quotas(scenario.id, {topics[1].id: 5})
    with pytest.raises(PackageValidationError) as exc:
        services.build_package(storage, scenario.id)
    assert "квота" in str(exc.value)


def test_scenario_policy_validation_blocks_export(storage):
    quiz = _single_quiz(storage)
    scenario = storage.create_scenario(
        quiz.id, "Плохой", grade_3_min_percent=90, grade_4_min_percent=80
    )
    with pytest.raises(PackageValidationError):
        services.build_package(storage, scenario.id)
    scenario.grade_3_min_percent, scenario.grade_4_min_percent = 60, 80
    scenario.questions_sample_size = 99
    storage.update_scenario(scenario)
    with pytest.raises(PackageValidationError) as exc:
        services.build_package(storage, scenario.id)
    assert "выборки" in str(exc.value)


def test_unlimited_attempts_and_auto_time_are_normalised(storage):
    quiz = _single_quiz(storage)
    scenario = storage.create_scenario(
        quiz.id, "S", attempts_unlimited=True, allowed_attempts=7, time_limit_minutes=5
    )
    room = services.build_package(storage, scenario.id)["room"]
    assert room["allowed_attempts"] is None
    assert room["time_limit_minutes"] is None


def test_duplicate_quiz_and_scenario(storage):
    quiz = _single_quiz(storage)
    scenario = storage.create_scenario(quiz.id, "S")
    copy = services.duplicate_quiz(storage, quiz.id)
    assert storage.count_questions(copy.id) == 3
    assert storage.list_scenarios(copy.id) == []
    scenario_copy = services.duplicate_scenario(storage, scenario.id)
    assert scenario_copy.public_id != scenario.public_id


def test_import_schema_variants_and_player_package_reimport(storage):
    bare = parse_import([{"text": "q", "options": [{"text": "a", "is_correct": True}, {"text": "b"}]}], "Файл")
    assert bare.title == "Файл" and bare.kind == "single"

    composite = parse_import(
        {
            "schema_version": 2,
            "kind": "composite",
            "title": "М",
            "topics": [{"title": "", "questions": [
                {"text": "q", "question_type": "single",
                 "options": [{"text": "a", "is_correct": True}, {"text": "b"}]}]}],
        }
    )
    assert composite.topics[0].title == "Тема 1"

    with pytest.raises(ImportDataError):
        parse_import({"title": "x", "questions": [{"text": "q", "options": []}]})

    quiz = _single_quiz(storage)
    scenario = storage.create_scenario(quiz.id, "Зачёт", allowed_attempts=4)
    package = services.build_package(storage, scenario.id)
    reimported = services.import_quiz(storage, parse_import(package))
    assert storage.count_questions(reimported.id) == 3
    [new_scenario] = storage.list_scenarios(reimported.id)
    assert new_scenario.allowed_attempts == 4
    assert new_scenario.public_id != scenario.public_id


def test_export_package_writes_utf8_file(storage, tmp_path):
    quiz = _single_quiz(storage, "Тест")
    scenario = storage.create_scenario(quiz.id, "Зачёт")
    target = tmp_path / services.suggested_filename(quiz, scenario)
    services.export_package(storage, scenario.id, target)
    assert "Тест" in target.read_text(encoding="utf-8")
    assert target.name == "Тест-Зачёт.json"
