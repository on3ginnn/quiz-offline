from quiz_offline.models import AnswerOption, Question, RoomPackage, RoomPolicy, TopicQuota
from quiz_offline.selection import build_attempt_layout, select_attempt_questions


def _make_package() -> RoomPackage:
    q1 = Question(
        1,
        "A",
        "single",
        [
            AnswerOption(101, "Да", True),
            AnswerOption(102, "Нет", False),
        ],
        topic_order=1,
    )
    q2 = Question(
        2,
        "B",
        "single",
        [
            AnswerOption(201, "Да", True),
            AnswerOption(202, "Нет", False),
        ],
        topic_order=1,
    )
    q3 = Question(
        3,
        "C",
        "single",
        [
            AnswerOption(301, "Да", True),
            AnswerOption(302, "Нет", False),
        ],
        topic_order=2,
    )
    room = RoomPolicy(
        name="R",
        public_id="uuid",
        time_limit_mode="auto",
        time_limit_minutes=None,
        attempts_unlimited=True,
        allowed_attempts=None,
        shuffle_questions=False,
        shuffle_options=False,
        selection_mode="per_attempt",
        show_results=True,
        show_answers=False,
        show_correct_answers=False,
        grade_3_min_percent=70,
        grade_4_min_percent=80,
        grade_5_min_percent=90,
        grade_attempt_mode="best",
        questions_sample_size=None,
    )
    return RoomPackage(
        exported_at="",
        quiz_title="T",
        quiz_kind="composite",
        questions=[q1, q2, q3],
        topics={1: [q1, q2], 2: [q3]},
        room=room,
        topic_quotas=[
            TopicQuota(1, "Тема 1", 2),
            TopicQuota(2, "Тема 2", 1),
        ],
    )


def test_composite_select_respects_quotas():
    pkg = _make_package()
    selected = select_attempt_questions(pkg)
    assert len(selected) == 3
    orders = [t for _q, t in selected]
    assert orders.count(1) == 2
    assert orders.count(2) == 1


def test_build_layout_has_option_order():
    pkg = _make_package()
    layout = build_attempt_layout(pkg)
    assert len(layout) == 3
    assert all(len(item.option_ids_order) == 2 for item in layout)
