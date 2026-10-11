"""SQLite-хранилище конструктора: тесты, темы, вопросы, сценарии, квоты."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

from quiz_admin.config import get_database_path
from quiz_admin.models import (
    POLICY_FIELDS,
    QUIZ_COMPOSITE,
    OptionDraft,
    QuestionDraft,
    Quiz,
    QuizSummary,
    Scenario,
    Topic,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    topic_order INTEGER NOT NULL,
    title TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    question_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    text TEXT NOT NULL,
    is_correct INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    public_id TEXT NOT NULL UNIQUE,
    time_limit_mode TEXT NOT NULL,
    time_limit_minutes INTEGER,
    attempts_unlimited INTEGER NOT NULL,
    allowed_attempts INTEGER,
    shuffle_questions INTEGER NOT NULL,
    shuffle_options INTEGER NOT NULL,
    selection_mode TEXT NOT NULL,
    show_results INTEGER NOT NULL,
    show_answers INTEGER NOT NULL,
    show_correct_answers INTEGER NOT NULL,
    grade_3_min_percent INTEGER NOT NULL,
    grade_4_min_percent INTEGER NOT NULL,
    grade_5_min_percent INTEGER NOT NULL,
    grade_attempt_mode TEXT NOT NULL,
    questions_sample_size INTEGER
);
CREATE TABLE IF NOT EXISTS scenario_topic_quotas (
    scenario_id INTEGER NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    question_count INTEGER NOT NULL,
    PRIMARY KEY (scenario_id, topic_id)
);
CREATE INDEX IF NOT EXISTS idx_questions_bank ON questions(quiz_id, topic_id, position);
"""

_BOOL_FIELDS = frozenset(
    {
        "attempts_unlimited",
        "shuffle_questions",
        "shuffle_options",
        "show_results",
        "show_answers",
        "show_correct_answers",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _scenario_from_row(row: sqlite3.Row) -> Scenario:
    values = {f.name: row[f.name] for f in fields(Scenario)}
    for name in _BOOL_FIELDS:
        values[name] = bool(values[name])
    return Scenario(**values)


class AdminStorage:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._path = Path(db_path) if db_path is not None else get_database_path()
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- тесты -----------------------------------------------------------

    def create_quiz(self, title: str, kind: str) -> Quiz:
        now = _now()
        cur = self._conn.execute(
            "INSERT INTO quizzes (title, kind, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title.strip(), kind, now, now),
        )
        self._conn.commit()
        return Quiz(cur.lastrowid, title.strip(), kind, now, now)

    def get_quiz(self, quiz_id: int) -> Quiz | None:
        row = self._conn.execute(
            "SELECT * FROM quizzes WHERE id = ?", (quiz_id,)
        ).fetchone()
        return self._quiz(row) if row else None

    @staticmethod
    def _quiz(row: sqlite3.Row) -> Quiz:
        return Quiz(row["id"], row["title"], row["kind"], row["created_at"], row["updated_at"])

    def list_quizzes(self) -> list[QuizSummary]:
        rows = self._conn.execute(
            """
            SELECT q.*,
              (SELECT COUNT(*) FROM questions x WHERE x.quiz_id = q.id) AS question_count,
              (SELECT COUNT(*) FROM topics t WHERE t.quiz_id = q.id) AS topic_count,
              (SELECT COUNT(*) FROM scenarios s WHERE s.quiz_id = q.id) AS scenario_count
            FROM quizzes q ORDER BY q.updated_at DESC, q.id DESC
            """
        ).fetchall()
        return [
            QuizSummary(
                self._quiz(r), r["question_count"], r["topic_count"], r["scenario_count"]
            )
            for r in rows
        ]

    def rename_quiz(self, quiz_id: int, title: str) -> None:
        self._conn.execute(
            "UPDATE quizzes SET title = ?, updated_at = ? WHERE id = ?",
            (title.strip(), _now(), quiz_id),
        )
        self._conn.commit()

    def touch_quiz(self, quiz_id: int) -> None:
        self._conn.execute(
            "UPDATE quizzes SET updated_at = ? WHERE id = ?", (_now(), quiz_id)
        )
        self._conn.commit()

    def delete_quiz(self, quiz_id: int) -> None:
        self._conn.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
        self._conn.commit()

    # --- темы ------------------------------------------------------------

    def list_topics(self, quiz_id: int) -> list[Topic]:
        rows = self._conn.execute(
            "SELECT * FROM topics WHERE quiz_id = ? ORDER BY topic_order, id", (quiz_id,)
        ).fetchall()
        return [Topic(r["id"], r["quiz_id"], r["topic_order"], r["title"]) for r in rows]

    def get_topic(self, topic_id: int) -> Topic | None:
        r = self._conn.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone()
        return Topic(r["id"], r["quiz_id"], r["topic_order"], r["title"]) if r else None

    def add_topic(self, quiz_id: int, title: str) -> Topic:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(topic_order), 0) + 1 FROM topics WHERE quiz_id = ?",
            (quiz_id,),
        ).fetchone()
        order = int(row[0])
        cur = self._conn.execute(
            "INSERT INTO topics (quiz_id, topic_order, title) VALUES (?, ?, ?)",
            (quiz_id, order, title.strip()),
        )
        self.touch_quiz(quiz_id)
        return Topic(cur.lastrowid, quiz_id, order, title.strip())

    def rename_topic(self, topic_id: int, title: str) -> None:
        topic = self.get_topic(topic_id)
        self._conn.execute(
            "UPDATE topics SET title = ? WHERE id = ?", (title.strip(), topic_id)
        )
        self._conn.commit()
        if topic:
            self.touch_quiz(topic.quiz_id)

    def delete_topic(self, topic_id: int) -> None:
        topic = self.get_topic(topic_id)
        self._conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        self._conn.commit()
        if topic:
            self.touch_quiz(topic.quiz_id)

    def move_topic(self, topic_id: int, delta: int) -> None:
        """Сдвинуть тему на соседнюю позицию (delta = -1 вверх, +1 вниз)."""
        topic = self.get_topic(topic_id)
        if topic is None:
            return
        topics = self.list_topics(topic.quiz_id)
        idx = next(i for i, t in enumerate(topics) if t.id == topic_id)
        j = idx + delta
        if not 0 <= j < len(topics):
            return
        other = topics[j]
        self._conn.execute(
            "UPDATE topics SET topic_order = ? WHERE id = ?", (other.topic_order, topic.id)
        )
        self._conn.execute(
            "UPDATE topics SET topic_order = ? WHERE id = ?", (topic.topic_order, other.id)
        )
        self._conn.commit()
        self.touch_quiz(topic.quiz_id)

    # --- вопросы ---------------------------------------------------------

    def list_questions(
        self, quiz_id: int, topic_id: int | None = None
    ) -> list[QuestionDraft]:
        rows = self._conn.execute(
            "SELECT * FROM questions WHERE quiz_id = ? AND topic_id IS ? ORDER BY position, id",
            (quiz_id, topic_id),
        ).fetchall()
        result: list[QuestionDraft] = []
        for r in rows:
            opts = self._conn.execute(
                "SELECT text, is_correct FROM options WHERE question_id = ? ORDER BY position, id",
                (r["id"],),
            ).fetchall()
            result.append(
                QuestionDraft(
                    text=r["text"],
                    question_type=r["question_type"],
                    options=[OptionDraft(o["text"], bool(o["is_correct"])) for o in opts],
                    id=r["id"],
                )
            )
        return result

    def count_questions(self, quiz_id: int, topic_id: int | None = None) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM questions WHERE quiz_id = ? AND topic_id IS ?",
            (quiz_id, topic_id),
        ).fetchone()
        return int(row[0])

    def replace_questions(
        self, quiz_id: int, topic_id: int | None, questions: list[QuestionDraft]
    ) -> None:
        """Заменить весь банк вопросов теста/темы (bulk-сохранение)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM questions WHERE quiz_id = ? AND topic_id IS ?",
                (quiz_id, topic_id),
            )
            for pos, q in enumerate(questions, start=1):
                cur = self._conn.execute(
                    "INSERT INTO questions (quiz_id, topic_id, position, text, question_type)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (quiz_id, topic_id, pos, q.text.strip(), q.question_type),
                )
                self._conn.executemany(
                    "INSERT INTO options (question_id, position, text, is_correct)"
                    " VALUES (?, ?, ?, ?)",
                    [
                        (cur.lastrowid, i, o.text.strip(), int(o.is_correct))
                        for i, o in enumerate(q.options, start=1)
                    ],
                )
        self.touch_quiz(quiz_id)

    # --- сценарии --------------------------------------------------------

    def create_scenario(self, quiz_id: int, name: str, **policy) -> Scenario:
        scenario = Scenario(
            id=0, quiz_id=quiz_id, name=name.strip(), public_id=str(uuid.uuid4()), **policy
        )
        columns = ["quiz_id", "name", "public_id", *POLICY_FIELDS]
        values = [getattr(scenario, c) for c in columns]
        cur = self._conn.execute(
            f"INSERT INTO scenarios ({', '.join(columns)}) "
            f"VALUES ({', '.join('?' * len(columns))})",
            values,
        )
        self._conn.commit()
        scenario.id = cur.lastrowid
        self.touch_quiz(quiz_id)
        return scenario

    def get_scenario(self, scenario_id: int) -> Scenario | None:
        row = self._conn.execute(
            "SELECT * FROM scenarios WHERE id = ?", (scenario_id,)
        ).fetchone()
        return _scenario_from_row(row) if row else None

    def list_scenarios(self, quiz_id: int) -> list[Scenario]:
        rows = self._conn.execute(
            "SELECT * FROM scenarios WHERE quiz_id = ? ORDER BY id", (quiz_id,)
        ).fetchall()
        return [_scenario_from_row(r) for r in rows]

    def update_scenario(self, scenario: Scenario) -> None:
        columns = ["name", *POLICY_FIELDS]
        self._conn.execute(
            f"UPDATE scenarios SET {', '.join(c + ' = ?' for c in columns)} WHERE id = ?",
            [getattr(scenario, c) for c in columns] + [scenario.id],
        )
        self._conn.commit()
        self.touch_quiz(scenario.quiz_id)

    def delete_scenario(self, scenario_id: int) -> None:
        scenario = self.get_scenario(scenario_id)
        self._conn.execute("DELETE FROM scenarios WHERE id = ?", (scenario_id,))
        self._conn.commit()
        if scenario:
            self.touch_quiz(scenario.quiz_id)

    def get_quotas(self, scenario_id: int) -> dict[int, int]:
        rows = self._conn.execute(
            "SELECT topic_id, question_count FROM scenario_topic_quotas WHERE scenario_id = ?",
            (scenario_id,),
        ).fetchall()
        return {r["topic_id"]: r["question_count"] for r in rows}

    def set_quotas(self, scenario_id: int, quotas: dict[int, int]) -> None:
        """Заменить квоты сценария целиком (темы без записи берутся целиком)."""
        with self._conn:
            self._conn.execute(
                "DELETE FROM scenario_topic_quotas WHERE scenario_id = ?", (scenario_id,)
            )
            self._conn.executemany(
                "INSERT INTO scenario_topic_quotas (scenario_id, topic_id, question_count)"
                " VALUES (?, ?, ?)",
                [(scenario_id, tid, int(cnt)) for tid, cnt in quotas.items()],
            )

    # --- служебное -------------------------------------------------------

    def quiz_is_composite(self, quiz_id: int) -> bool:
        quiz = self.get_quiz(quiz_id)
        return bool(quiz and quiz.kind == QUIZ_COMPOSITE)
