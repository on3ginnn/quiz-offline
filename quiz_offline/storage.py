"""SQLite: библиотека комнат, участники, попытки."""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quiz_offline.config import get_database_path, get_rooms_dir
from quiz_offline.models import RoomPackage
from quiz_offline.room_loader import (
    RoomPackageError,
    load_room_package_from_path,
    normalize_full_name,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _compare_attempts(a: dict, b: dict) -> int:
    """Положительное — a лучше b."""
    for key in ("grade", "weighted_percent", "score"):
        av = int(a.get(key) or 0)
        bv = int(b.get(key) or 0)
        if av != bv:
            return 1 if av > bv else -1
    return 0


@dataclass
class RegisteredRoomRow:
    id: int
    room_public_id: str
    quiz_title: str
    room_name: str
    package_rel_path: str
    added_at: str
    package_updated_at: str
    last_opened_at: str | None
    participant_count: int  # участники с ≥1 завершённой попыткой
    attempt_count: int
    last_attempt_at: str | None
    package_exists: bool


@dataclass
class HallParticipantRow:
    participant_id: int
    full_name_display: str
    attempt_count: int
    last_finished_at: str | None
    last_duration_sec: int | None
    last_weighted_percent: int | None
    last_grade: int | None
    best_weighted_percent: int | None
    best_grade: int | None


class Storage:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS registered_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_public_id TEXT NOT NULL UNIQUE,
                quiz_title TEXT NOT NULL,
                room_name TEXT NOT NULL,
                package_rel_path TEXT NOT NULL,
                added_at TEXT NOT NULL,
                package_updated_at TEXT NOT NULL,
                last_opened_at TEXT
            );
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_public_id TEXT NOT NULL,
                full_name_normalized TEXT NOT NULL,
                full_name_display TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                UNIQUE(room_public_id, full_name_normalized)
            );
            CREATE TABLE IF NOT EXISTS participant_topic_selections (
                participant_id INTEGER NOT NULL,
                topic_order INTEGER NOT NULL,
                question_ids_json TEXT NOT NULL,
                PRIMARY KEY (participant_id, topic_order),
                FOREIGN KEY (participant_id) REFERENCES participants(id)
            );
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                duration_sec INTEGER NOT NULL,
                total_questions INTEGER NOT NULL,
                score INTEGER NOT NULL,
                weighted_sum REAL NOT NULL,
                weighted_percent INTEGER NOT NULL,
                grade INTEGER NOT NULL,
                question_layout_json TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                FOREIGN KEY (participant_id) REFERENCES participants(id)
            );
            """
        )
        self._conn.commit()

    def list_registered_rooms(self) -> list[RegisteredRoomRow]:
        rows = self._conn.execute(
            """
            SELECT r.*,
                   (
                       SELECT COUNT(DISTINCT p.id)
                       FROM participants p
                       INNER JOIN attempts a ON a.participant_id = p.id
                       WHERE p.room_public_id = r.room_public_id
                   ) AS participant_count,
                   (
                       SELECT COUNT(*)
                       FROM attempts a
                       JOIN participants p ON a.participant_id = p.id
                       WHERE p.room_public_id = r.room_public_id
                   ) AS attempt_count,
                   (
                       SELECT MAX(a.finished_at)
                       FROM attempts a
                       JOIN participants p ON a.participant_id = p.id
                       WHERE p.room_public_id = r.room_public_id
                   ) AS last_attempt_at
            FROM registered_rooms r
            ORDER BY COALESCE(r.last_opened_at, r.added_at) DESC
            """
        ).fetchall()
        rooms_dir = get_rooms_dir()
        result: list[RegisteredRoomRow] = []
        for row in rows:
            rel = row["package_rel_path"]
            exists = (rooms_dir / rel).is_file()
            result.append(
                RegisteredRoomRow(
                    id=row["id"],
                    room_public_id=row["room_public_id"],
                    quiz_title=row["quiz_title"],
                    room_name=row["room_name"],
                    package_rel_path=rel,
                    added_at=row["added_at"],
                    package_updated_at=row["package_updated_at"],
                    last_opened_at=row["last_opened_at"],
                    participant_count=int(row["participant_count"] or 0),
                    attempt_count=int(row["attempt_count"] or 0),
                    last_attempt_at=row["last_attempt_at"],
                    package_exists=exists,
                )
            )
        return result

    def register_room_from_file(
        self, source_path: Path, *, update_if_exists: bool = False
    ) -> tuple[RegisteredRoomRow, bool]:
        """
        Добавить комнату из JSON. Возвращает (row, was_updated).
        was_updated=False для новой записи.
        """
        package = load_room_package_from_path(source_path)
        if package.room is None:
            raise RoomPackageError("В пакете нет room.")
        public_id = package.room.public_id
        existing = self._conn.execute(
            "SELECT * FROM registered_rooms WHERE room_public_id = ?",
            (public_id,),
        ).fetchone()

        if existing and not update_if_exists:
            raise RoomPackageError(
                "Комната уже добавлена. Подтвердите обновление пакета."
            )

        dest_name = f"{public_id}.json"
        dest_path = get_rooms_dir() / dest_name
        shutil.copy2(source_path, dest_path)
        now = _utc_now_iso()

        if existing:
            self._conn.execute(
                """
                UPDATE registered_rooms
                SET quiz_title = ?, room_name = ?, package_rel_path = ?,
                    package_updated_at = ?
                WHERE room_public_id = ?
                """,
                (
                    package.quiz_title,
                    package.room.name,
                    dest_name,
                    now,
                    public_id,
                ),
            )
            self._conn.commit()
            was_updated = True
        else:
            self._conn.execute(
                """
                INSERT INTO registered_rooms (
                    room_public_id, quiz_title, room_name,
                    package_rel_path, added_at, package_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    public_id,
                    package.quiz_title,
                    package.room.name,
                    dest_name,
                    now,
                    now,
                ),
            )
            self._conn.commit()
            was_updated = False

        row = self._get_registered_room(public_id)
        assert row is not None
        return row, was_updated

    def touch_room_opened(self, room_public_id: str) -> None:
        self._conn.execute(
            "UPDATE registered_rooms SET last_opened_at = ? WHERE room_public_id = ?",
            (_utc_now_iso(), room_public_id),
        )
        self._conn.commit()

    def _get_registered_room(self, room_public_id: str) -> RegisteredRoomRow | None:
        for row in self.list_registered_rooms():
            if row.room_public_id == room_public_id:
                return row
        return None

    def load_package_for_room(self, room_public_id: str) -> RoomPackage:
        row = self._conn.execute(
            "SELECT package_rel_path FROM registered_rooms WHERE room_public_id = ?",
            (room_public_id,),
        ).fetchone()
        if row is None:
            raise RoomPackageError("Комната не найдена в библиотеке.")
        path = get_rooms_dir() / row["package_rel_path"]
        if not path.is_file():
            raise RoomPackageError(
                "Файл пакета не найден. Укажите JSON снова через «Добавить тест»."
            )
        return load_room_package_from_path(path)

    def relink_room_package(self, room_public_id: str, source_path: Path) -> None:
        self.register_room_from_file(source_path, update_if_exists=True)

    def remove_registered_room(self, room_public_id: str) -> None:
        """Убрать комнату из библиотеки; журнал участников в БД сохраняется."""
        row = self._conn.execute(
            "SELECT package_rel_path FROM registered_rooms WHERE room_public_id = ?",
            (room_public_id,),
        ).fetchone()
        if row is None:
            return
        rel = row["package_rel_path"]
        self._conn.execute(
            "DELETE FROM registered_rooms WHERE room_public_id = ?",
            (room_public_id,),
        )
        self._conn.commit()
        pkg_path = get_rooms_dir() / rel
        if pkg_path.is_file():
            pkg_path.unlink()

    def list_hall_participants(self, room_public_id: str) -> list[HallParticipantRow]:
        participants = self._conn.execute(
            """
            SELECT id, full_name_display
            FROM participants
            WHERE room_public_id = ?
            """,
            (room_public_id,),
        ).fetchall()
        result: list[HallParticipantRow] = []
        for p in participants:
            attempts = self._conn.execute(
                """
                SELECT finished_at, duration_sec, weighted_percent, grade, score
                FROM attempts
                WHERE participant_id = ?
                ORDER BY finished_at DESC
                """,
                (p["id"],),
            ).fetchall()
            if not attempts:
                continue
            last = attempts[0]
            best = attempts[0]
            for att in attempts[1:]:
                if _compare_attempts(dict(att), dict(best)) > 0:
                    best = att
            result.append(
                HallParticipantRow(
                    participant_id=p["id"],
                    full_name_display=p["full_name_display"],
                    attempt_count=len(attempts),
                    last_finished_at=last["finished_at"],
                    last_duration_sec=last["duration_sec"],
                    last_weighted_percent=last["weighted_percent"],
                    last_grade=last["grade"],
                    best_weighted_percent=best["weighted_percent"],
                    best_grade=best["grade"],
                )
            )
        result.sort(
            key=lambda r: r.last_finished_at or "",
            reverse=True,
        )
        return result

    def get_or_create_participant(
        self, room_public_id: str, full_name_display: str
    ) -> int:
        normalized = normalize_full_name(full_name_display)
        if not normalized:
            raise ValueError("Введите ФИО.")
        row = self._conn.execute(
            """
            SELECT id FROM participants
            WHERE room_public_id = ? AND full_name_normalized = ?
            """,
            (room_public_id, normalized),
        ).fetchone()
        if row:
            return int(row["id"])
        now = _utc_now_iso()
        cur = self._conn.execute(
            """
            INSERT INTO participants (
                room_public_id, full_name_normalized,
                full_name_display, first_seen_at
            ) VALUES (?, ?, ?, ?)
            """,
            (room_public_id, normalized, full_name_display.strip(), now),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def count_attempts(self, participant_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM attempts WHERE participant_id = ?",
            (participant_id,),
        ).fetchone()
        return int(row["c"] or 0)

    def load_participant_selections(self, participant_id: int) -> dict[int, list[int]]:
        rows = self._conn.execute(
            """
            SELECT topic_order, question_ids_json
            FROM participant_topic_selections
            WHERE participant_id = ?
            """,
            (participant_id,),
        ).fetchall()
        result: dict[int, list[int]] = {}
        for row in rows:
            ids = json.loads(row["question_ids_json"])
            result[int(row["topic_order"])] = [int(x) for x in ids]
        return result

    def save_participant_selections(
        self, participant_id: int, selections: dict[int, list[int]]
    ) -> None:
        for topic_order, ids in selections.items():
            self._conn.execute(
                """
                INSERT INTO participant_topic_selections (
                    participant_id, topic_order, question_ids_json
                ) VALUES (?, ?, ?)
                ON CONFLICT(participant_id, topic_order) DO UPDATE SET
                    question_ids_json = excluded.question_ids_json
                """,
                (participant_id, topic_order, json.dumps(ids)),
            )
        self._conn.commit()

    def save_attempt(
        self,
        participant_id: int,
        *,
        started_at: str,
        finished_at: str,
        duration_sec: int,
        total_questions: int,
        score: int,
        weighted_sum: float,
        weighted_percent: int,
        grade: int,
        layout_json: list[dict[str, Any]],
        answers_json: dict[int, list[int]],
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO attempts (
                participant_id, started_at, finished_at, duration_sec,
                total_questions, score, weighted_sum, weighted_percent,
                grade, question_layout_json, answers_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                participant_id,
                started_at,
                finished_at,
                duration_sec,
                total_questions,
                score,
                weighted_sum,
                weighted_percent,
                grade,
                json.dumps(layout_json, ensure_ascii=False),
                json.dumps(
                    {str(k): v for k, v in answers_json.items()},
                    ensure_ascii=False,
                ),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)
