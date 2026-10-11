import json
from pathlib import Path

from quiz_offline.room_loader import parse_room_package_dict
from quiz_offline.ui.room_meta import (
    build_room_card_meta,
    build_room_meta_labels,
    estimate_questions_per_attempt,
)
from tests.player.test_room_loader import _sample_v3_single


def test_estimate_questions_single_full_bank():
    pkg = parse_room_package_dict(_sample_v3_single())
    assert estimate_questions_per_attempt(pkg) == 1


def test_estimate_questions_single_sample_size():
    data = _sample_v3_single()
    data["quiz"]["questions"] = [
        {
            "text": f"Q{i}",
            "question_type": "single",
            "options": [
                {"text": "Да", "is_correct": True},
                {"text": "Нет", "is_correct": False},
            ],
        }
        for i in range(10)
    ]
    data["room"]["questions_sample_size"] = 5
    pkg = parse_room_package_dict(data)
    assert estimate_questions_per_attempt(pkg) == 5


def test_build_room_meta_labels_contains_attempts_and_minutes():
    pkg = parse_room_package_dict(_sample_v3_single())
    labels = build_room_meta_labels(pkg)
    assert any("попыт" in label for label in labels)
    assert any("мин" in label for label in labels)
    assert any("вопрос" in label for label in labels)


def test_build_room_card_meta_order():
    pkg = parse_room_package_dict(_sample_v3_single())
    meta = build_room_card_meta(pkg, tested_participant_count=4)
    assert meta.home_badges[0] == "3 попытки"
    assert meta.home_badges[1] == "👥 4"
    assert "мин" in meta.home_badges[2]
    assert "вопрос" in meta.home_badges[3]
