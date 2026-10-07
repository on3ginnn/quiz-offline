import json
from pathlib import Path

import pytest

from quiz_offline.room_loader import RoomPackageError, parse_room_package_dict


def _sample_v3_single() -> dict:
    return {
        "schema_version": 3,
        "kind": "room_package",
        "exported_at": "2026-06-20T12:00:00+03:00",
        "quiz": {
            "title": "Тест",
            "kind": "single",
            "questions": [
                {
                    "text": "Q1",
                    "question_type": "single",
                    "options": [
                        {"text": "Да", "is_correct": True},
                        {"text": "Нет", "is_correct": False},
                    ],
                }
            ],
        },
        "room": {
            "name": "Комната",
            "public_id": "11111111-1111-1111-1111-111111111111",
            "time_limit_mode": "manual",
            "time_limit_minutes": 30,
            "attempts_unlimited": False,
            "allowed_attempts": 3,
            "shuffle_questions": False,
            "shuffle_options": False,
            "selection_mode": "per_attempt",
            "show_results": True,
            "show_answers": False,
            "show_correct_answers": False,
            "grade_3_min_percent": 70,
            "grade_4_min_percent": 80,
            "grade_5_min_percent": 90,
            "grade_attempt_mode": "best",
            "questions_sample_size": None,
        },
        "topic_quotas": [],
    }


def test_parse_room_package_v3_single():
    pkg = parse_room_package_dict(_sample_v3_single())
    assert pkg.quiz_kind == "single"
    assert len(pkg.questions) == 1
    assert pkg.room is not None
    assert pkg.room.allowed_attempts == 3


def test_parse_rejects_wrong_schema():
    data = _sample_v3_single()
    data["schema_version"] = 2
    with pytest.raises(RoomPackageError):
        parse_room_package_dict(data)


def test_load_from_file(tmp_path: Path):
    path = tmp_path / "room.json"
    path.write_text(json.dumps(_sample_v3_single()), encoding="utf-8")
    from quiz_offline.room_loader import load_room_package_from_path

    pkg = load_room_package_from_path(path)
    assert pkg.quiz_title == "Тест"
