"""Экран прохождения теста."""

from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import QEvent, Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from quiz_offline.attempt_grading import grade_attempt
from quiz_offline.models import AttemptLayoutItem
from quiz_offline.room_loader import RoomPackageError
from quiz_offline.selection import build_attempt_layout, effective_time_limit_minutes
from quiz_offline.storage import Storage
from quiz_offline.ui.message_boxes import ask_yes_no
from quiz_offline.ui.page_header import PageHeader
from quiz_offline.ui.qt_helpers import is_checkbox_checked
from quiz_offline.ui.taking_keyboard import (
    build_taking_focus_chain,
    move_focus_in_chain,
)
from quiz_offline.ui.wrapped_options import (
    build_multiple_choice_row,
    build_single_choice_row,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TakingWidget(QWidget):
    finished_attempt = pyqtSignal(dict)
    cancelled = pyqtSignal()

    def __init__(self, storage: Storage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.storage = storage
        self._layout: list[AttemptLayoutItem] = []
        self._answers: dict[int, list[int]] = {}
        self._index = 0
        self._remaining_sec = 0
        self._started_at = ""
        self._room_public_id = ""
        self._participant_id = 0
        self._full_name = ""
        self._room_policy = None
        self._option_buttons: list[QWidget] = []

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)

        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        # Контент прижат к верху; лишняя высота окна — только снизу
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.finish_btn = QPushButton("Завершить попытку")
        self.finish_btn.setObjectName("textAction")
        self.finish_btn.clicked.connect(self._confirm_finish)

        self.header = PageHeader(
            self,
            on_back=self._confirm_leave,
            back_tooltip="В зал",
        )
        self.header.set_trailing(self.finish_btn)
        self.header.set_meta_badges([])
        self.header.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        outer.addWidget(self.header)

        progress_row = QHBoxLayout()
        self.progress_label = QLabel()
        self.progress_label.setObjectName("subtitle")
        self.progress_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        progress_row.addWidget(
            self.progress_label, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        progress_row.addStretch()
        self.timer_label = QLabel()
        self.timer_label.setObjectName("timerBadge")
        self.timer_label.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum
        )
        progress_row.addWidget(
            self.timer_label, alignment=Qt.AlignmentFlag.AlignVCenter
        )
        outer.addLayout(progress_row)

        self.question_card = QFrame()
        self.question_card.setObjectName("questionCard")
        self.question_card.setAutoFillBackground(False)
        self.question_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        card_layout = QVBoxLayout(self.question_card)
        card_layout.setContentsMargins(16, 12, 16, 12)
        card_layout.setSpacing(12)
        self.question_label = QLabel()
        self.question_label.setObjectName("questionText")
        self.question_label.setWordWrap(True)
        self.question_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.question_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        card_layout.addWidget(self.question_label)
        self.options_container = QVBoxLayout()
        self.options_container.setSpacing(6)
        card_layout.addLayout(self.options_container)
        outer.addWidget(self.question_card)

        nav = QHBoxLayout()
        nav.setSpacing(10)
        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("navIcon")
        self.prev_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        )
        self.prev_btn.setIconSize(QSize(22, 22))
        self.prev_btn.setToolTip("Назад")
        self.prev_btn.clicked.connect(self._prev)
        nav.addWidget(self.prev_btn)
        self.next_btn = QPushButton("Следующий →")
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(self._next)
        nav.addWidget(self.next_btn)
        self.clear_btn = QPushButton("Очистить выбор")
        self.clear_btn.setObjectName("takingFooterBtn")
        self.clear_btn.clicked.connect(self._clear_selection)
        self.clear_btn.setVisible(False)
        nav.addWidget(self.clear_btn)
        nav.addStretch()
        outer.addLayout(nav)
        outer.addStretch(1)

        for btn in (self.prev_btn, self.next_btn, self.clear_btn):
            btn.installEventFilter(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_wrap_widths()

    def _sync_wrap_widths(self) -> None:
        """QLabel переносит строки только при ограниченной ширине."""
        w = self.width()
        if w <= 0:
            return
        outer_m = self.layout().contentsMargins()
        available = w - outer_m.left() - outer_m.right()
        margins = self.question_card.layout().contentsMargins()
        inner_w = max(120, available - margins.left() - margins.right())
        self.question_label.setMaximumWidth(inner_w)

    def _build_focus_chain(self) -> list[QWidget]:
        return build_taking_focus_chain(
            self._option_buttons,
            self.next_btn,
            self.prev_btn,
            self.clear_btn,
        )

    def _apply_tab_order(self) -> None:
        chain = self._build_focus_chain()
        for i in range(len(chain) - 1):
            QWidget.setTabOrder(chain[i], chain[i + 1])

    def _focus_first_in_chain(self) -> None:
        chain = self._build_focus_chain()
        if chain:
            chain[0].setFocus()

    def eventFilter(self, obj, event) -> bool:
        # Стрелки ↑↓ — единая цепочка: варианты → Следующий → Назад → Очистить
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                chain = self._build_focus_chain()
                focused = self.focusWidget()
                if obj in chain or focused in chain:
                    delta = 1 if key == Qt.Key.Key_Down else -1
                    move_focus_in_chain(chain, focused, delta)
                    return True
        return super().eventFilter(obj, event)

    def start_attempt(
        self, room_public_id: str, participant_id: int, full_name: str
    ) -> None:
        try:
            package = self.storage.load_package_for_room(room_public_id)
        except RoomPackageError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            self.cancelled.emit()
            return

        room = package.room
        assert room is not None
        selections = self.storage.load_participant_selections(participant_id)
        try:
            self._layout = build_attempt_layout(package, selections)
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            self.cancelled.emit()
            return

        if room.selection_mode == "per_participant":
            self.storage.save_participant_selections(participant_id, selections)

        self._room_public_id = room_public_id
        self._participant_id = participant_id
        self._full_name = full_name
        self._room_policy = room
        self._answers = {}
        self._index = 0
        self._started_at = _utc_now_iso()
        mins = effective_time_limit_minutes(room, len(self._layout))
        self._remaining_sec = mins * 60

        self.header.set_title(package.quiz_title)
        self.header.set_subtitle("")
        self._render_question()
        self._timer.start()

    def _tick(self) -> None:
        self._remaining_sec -= 1
        self._update_timer_label()
        if self._remaining_sec <= 0:
            self._timer.stop()
            self._submit(finished_by_timer=True)

    def _update_timer_label(self) -> None:
        m, s = divmod(max(0, self._remaining_sec), 60)
        self.timer_label.setText(f"⏱ {m:02d}:{s:02d}")

    def _current_question_id(self) -> int | None:
        if not self._layout:
            return None
        return self._layout[self._index].question.id

    def _update_clear_btn_visibility(self) -> None:
        qid = self._current_question_id()
        has_selection = bool(qid is not None and self._answers.get(qid))
        self.clear_btn.setVisible(has_selection)

    def _render_question(self) -> None:
        if not self._layout:
            return
        item = self._layout[self._index]
        q = item.question
        self.progress_label.setText(
            f"Вопрос {self._index + 1} из {len(self._layout)}"
        )
        self.question_label.setText(q.text)
        self.prev_btn.setEnabled(self._index > 0)
        self.next_btn.setText(
            "Завершить тест"
            if self._index >= len(self._layout) - 1
            else "Следующий →"
        )

        while self.options_container.count():
            child = self.options_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._option_buttons = []
        selected = set(self._answers.get(q.id, []))
        opts_by_id = {o.id: o for o in q.options}
        if q.question_type == "single":
            group = QButtonGroup(self)
            group.setExclusive(True)
            for oid in item.option_ids_order:
                opt = opts_by_id[oid]
                row, rb = build_single_choice_row(
                    opt.text,
                    checked=oid in selected,
                    parent=self.question_card,
                )
                rb.toggled.connect(
                    lambda checked, qid=q.id, oid=oid: self._on_single(
                        qid, oid, checked
                    )
                )
                group.addButton(rb)
                self.options_container.addWidget(row)
                self._option_buttons.append(rb)
                rb.installEventFilter(self)
        else:
            for oid in item.option_ids_order:
                opt = opts_by_id[oid]
                row, cb = build_multiple_choice_row(
                    opt.text,
                    checked=oid in selected,
                    parent=self.question_card,
                )
                cb.stateChanged.connect(
                    lambda state, qid=q.id, oid=oid: self._on_multiple(
                        qid, oid, state
                    )
                )
                self.options_container.addWidget(row)
                self._option_buttons.append(cb)
                cb.installEventFilter(self)

        self._sync_wrap_widths()

        self._update_timer_label()
        self._update_clear_btn_visibility()
        self._apply_tab_order()
        self._focus_first_in_chain()

    def _on_single(self, qid: int, oid: int, checked: bool) -> None:
        if checked:
            self._answers[qid] = [oid]
        self._update_clear_btn_visibility()

    def _on_multiple(self, qid: int, oid: int, state) -> None:
        current = set(self._answers.get(qid, []))
        if is_checkbox_checked(state):
            current.add(oid)
        else:
            current.discard(oid)
        self._answers[qid] = sorted(current)
        self._update_clear_btn_visibility()

    def _clear_selection(self) -> None:
        if not self._layout:
            return
        qid = self._layout[self._index].question.id
        self._answers[qid] = []
        self._render_question()

    def _prev(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._render_question()

    def _confirm_finish(self) -> None:
        if ask_yes_no(
            self,
            "Завершить попытку",
            "Завершить попытку и показать результат?",
        ):
            self._submit(finished_by_timer=False)

    def _confirm_leave(self) -> None:
        if ask_yes_no(
            self,
            "Выйти в зал",
            "Прервать попытку и вернуться в зал? Ответы не сохранятся.",
        ):
            self._timer.stop()
            self.cancelled.emit()

    def _next(self) -> None:
        if self._index < len(self._layout) - 1:
            self._index += 1
            self._render_question()
        else:
            self._confirm_finish()

    def _submit(self, *, finished_by_timer: bool) -> None:
        self._timer.stop()
        finished_at = _utc_now_iso()
        started = datetime.fromisoformat(self._started_at)
        finished = datetime.fromisoformat(finished_at)
        duration_sec = max(0, int((finished - started).total_seconds()))
        room = self._room_policy
        assert room is not None
        result = grade_attempt(
            self._layout,
            self._answers,
            thresholds=room.grade_thresholds(),
            duration_sec=duration_sec,
        )
        layout_json = [
            {
                "question_id": item.question.id,
                "topic_order": item.topic_order,
                "option_ids_order": item.option_ids_order,
            }
            for item in self._layout
        ]
        attempt_id = self.storage.save_attempt(
            self._participant_id,
            started_at=self._started_at,
            finished_at=finished_at,
            duration_sec=duration_sec,
            total_questions=result.total_questions,
            score=result.score,
            weighted_sum=result.weighted_sum,
            weighted_percent=result.weighted_percent,
            grade=result.grade,
            layout_json=layout_json,
            answers_json=result.answers,
        )
        used = self.storage.count_attempts(self._participant_id)
        cap = room.attempts_cap()
        remaining = None if cap is None else max(0, cap - used)
        self.finished_attempt.emit(
            {
                "attempt_id": attempt_id,
                "participant_id": self._participant_id,
                "full_name": self._full_name,
                "room_public_id": self._room_public_id,
                "result": result,
                "remaining_attempts": remaining,
                "show_results": room.show_results,
                "finished_by_timer": finished_by_timer,
            }
        )
