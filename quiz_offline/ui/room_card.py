"""Карточка комнаты на главном экране."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from quiz_offline.storage import RegisteredRoomRow
from quiz_offline.ui.meta_badges_row import MetaBadgesRow

_KIND_ICONS = {
    "composite": "📚",
    "single": "📝",
}


def _kind_icon(quiz_kind: str) -> str:
    return _KIND_ICONS.get((quiz_kind or "single").strip(), "📝")


class RoomCard(QFrame):
    """Карточка зарегистрированной комнаты с явным CTA «Войти»."""

    enter_clicked = pyqtSignal(str)
    update_requested = pyqtSignal(str)

    def __init__(
        self,
        row: RegisteredRoomRow,
        *,
        quiz_kind: str = "single",
        badge_labels: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._room_public_id = row.room_public_id
        self.setObjectName("roomCard")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_badge = QFrame()
        icon_badge.setObjectName("roomCardIconBadge")
        icon_badge.setFixedSize(56, 56)
        badge_layout = QVBoxLayout(icon_badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(_kind_icon(quiz_kind))
        icon_lbl.setObjectName("roomCardIcon")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge_layout.addWidget(icon_lbl)
        root.addWidget(icon_badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(10)
        text_col.setContentsMargins(0, 0, 0, 0)

        heading = QLabel(f"{row.quiz_title} · {row.room_name}")
        heading.setObjectName("roomCardHeading")
        heading.setWordWrap(True)
        text_col.addWidget(heading)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        stats_row.setContentsMargins(0, 0, 0, 0)
        meta_badges = MetaBadgesRow()
        labels = list(badge_labels or [])
        if not labels:
            labels = [f"👥 {row.participant_count}"]
        tooltips: list[str | None] = []
        for label in labels:
            if "попыт" in label or "ограничения" in label:
                tooltips.append("Разрешено попыток по настройкам комнаты")
            elif label.startswith("Прошли"):
                tooltips.append("Прошли тест хотя бы раз")
            else:
                tooltips.append(None)
        meta_badges.set_labels(labels, tooltips=tooltips)
        stats_row.addWidget(meta_badges)

        if not row.package_exists:
            warn = QLabel("файл не найден")
            warn.setObjectName("roomCardWarn")
            stats_row.addWidget(warn)

        stats_row.addStretch()
        text_col.addLayout(stats_row)
        root.addLayout(text_col, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        enter_btn = QPushButton("Войти →")
        enter_btn.setObjectName("roomEnterPrimary")
        enter_btn.clicked.connect(self._emit_enter)
        actions.addWidget(enter_btn)

        menu_btn = QToolButton()
        menu_btn.setObjectName("roomMenuBtn")
        menu_btn.setText("⋮")
        menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu_btn.setToolTip("Ещё: заменить файл пакета")
        menu_btn.setAccessibleName("Дополнительные действия")
        menu = QMenu(menu_btn)
        menu.setObjectName("roomCardMenu")
        menu.addAction("Заменить файл комнаты…", self._emit_update)
        menu_btn.setMenu(menu)
        actions.addWidget(menu_btn)
        root.addLayout(actions)

    def _emit_enter(self) -> None:
        self.enter_clicked.emit(self._room_public_id)

    def _emit_update(self) -> None:
        self.update_requested.emit(self._room_public_id)
