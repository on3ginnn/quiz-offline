import json
from pathlib import Path

from quiz_offline.storage import Storage
from quiz_offline.ui.formatters import format_attempts_allowance
from tests.player.test_room_loader import _sample_v3_single


def test_register_and_hall_aggregates(tmp_path: Path):
    db = tmp_path / "journal.sqlite"
    storage = Storage(db)
    pkg_path = tmp_path / "pkg.json"
    pkg_path.write_text(json.dumps(_sample_v3_single()), encoding="utf-8")

    # monkeypatch rooms dir - storage uses get_rooms_dir from config
    import quiz_offline.storage as storage_mod

    rooms_dir = tmp_path / "rooms"
    rooms_dir.mkdir()
    original = storage_mod.get_rooms_dir
    storage_mod.get_rooms_dir = lambda: rooms_dir
    try:
        row, updated = storage.register_room_from_file(pkg_path)
        assert not updated
        pkg = storage.load_package_for_room(row.room_public_id)
        assert pkg.room is not None
        assert format_attempts_allowance(
            unlimited=pkg.room.attempts_unlimited,
            allowed=pkg.room.allowed_attempts,
        ) == "3 попытки"
        pid = storage.get_or_create_participant(
            row.room_public_id, "Иванов Иван"
        )
        storage.save_attempt(
            pid,
            started_at="2026-01-01T10:00:00+00:00",
            finished_at="2026-01-01T10:30:00+00:00",
            duration_sec=1800,
            total_questions=10,
            score=8,
            weighted_sum=7.5,
            weighted_percent=75,
            grade=3,
            layout_json=[],
            answers_json={},
        )
        storage.save_attempt(
            pid,
            started_at="2026-01-02T10:00:00+00:00",
            finished_at="2026-01-02T10:20:00+00:00",
            duration_sec=1200,
            total_questions=10,
            score=10,
            weighted_sum=9.0,
            weighted_percent=90,
            grade=5,
            layout_json=[],
            answers_json={},
        )
        hall = storage.list_hall_participants(row.room_public_id)
        assert len(hall) == 1
        assert hall[0].attempt_count == 2
        assert hall[0].last_grade == 5
        assert hall[0].best_grade == 5

        listed = storage.list_registered_rooms()
        assert listed[0].attempt_count == 2
        assert listed[0].last_attempt_at is not None
        assert listed[0].participant_count == len(hall)
    finally:
        storage_mod.get_rooms_dir = original
        storage.close()


def test_participant_count_only_with_attempts(tmp_path: Path):
    """Счётчик «Прошли» на карточке совпадает с числом строк в зале."""
    db = tmp_path / "journal.sqlite"
    storage = Storage(db)
    pkg_path = tmp_path / "pkg.json"
    pkg_path.write_text(json.dumps(_sample_v3_single()), encoding="utf-8")

    import quiz_offline.storage as storage_mod

    rooms_dir = tmp_path / "rooms"
    rooms_dir.mkdir()
    original = storage_mod.get_rooms_dir
    storage_mod.get_rooms_dir = lambda: rooms_dir
    try:
        row, _ = storage.register_room_from_file(pkg_path)
        storage.get_or_create_participant(row.room_public_id, "Без попытки")
        pid_with = storage.get_or_create_participant(
            row.room_public_id, "С попыткой"
        )
        storage.save_attempt(
            pid_with,
            started_at="2026-01-01T10:00:00+00:00",
            finished_at="2026-01-01T10:10:00+00:00",
            duration_sec=600,
            total_questions=1,
            score=1,
            weighted_sum=1.0,
            weighted_percent=100,
            grade=5,
            layout_json=[],
            answers_json={},
        )

        hall = storage.list_hall_participants(row.room_public_id)
        listed = storage.list_registered_rooms()
        assert len(hall) == 1
        assert listed[0].participant_count == 1
        assert listed[0].participant_count == len(hall)
    finally:
        storage_mod.get_rooms_dir = original
        storage.close()


def test_remove_registered_room(tmp_path: Path):
    db = tmp_path / "journal.sqlite"
    storage = Storage(db)
    pkg_path = tmp_path / "pkg.json"
    pkg_path.write_text(json.dumps(_sample_v3_single()), encoding="utf-8")

    import quiz_offline.storage as storage_mod

    rooms_dir = tmp_path / "rooms"
    rooms_dir.mkdir()
    original = storage_mod.get_rooms_dir
    storage_mod.get_rooms_dir = lambda: rooms_dir
    try:
        row, _ = storage.register_room_from_file(pkg_path)
        pkg_file = rooms_dir / row.package_rel_path
        assert pkg_file.is_file()
        pid = storage.get_or_create_participant(row.room_public_id, "Петров Пётр")
        storage.save_attempt(
            pid,
            started_at="2026-01-01T10:00:00+00:00",
            finished_at="2026-01-01T10:10:00+00:00",
            duration_sec=600,
            total_questions=10,
            score=5,
            weighted_sum=5.0,
            weighted_percent=50,
            grade=3,
            layout_json=[],
            answers_json={},
        )

        storage.remove_registered_room(row.room_public_id)
        assert storage.list_registered_rooms() == []
        assert not pkg_file.is_file()
        # Журнал участников сохраняется после удаления из библиотеки
        hall = storage.list_hall_participants(row.room_public_id)
        assert len(hall) == 1
        assert hall[0].full_name_display == "Петров Пётр"
    finally:
        storage_mod.get_rooms_dir = original
        storage.close()
