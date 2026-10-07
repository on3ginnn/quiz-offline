"""Экран Home: библиотека комнат и добавление JSON."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from quiz_offline.room_loader import RoomPackageError
from quiz_offline.storage import RegisteredRoomRow, Storage
from quiz_offline.ui.room_meta import RoomCardMeta, build_room_card_meta
from quiz_offline.ui.message_boxes import ask_yes_no
from quiz_offline.ui.room_card import RoomCard


class _EmptyRoomsState(QWidget):
    """Пустое состояние, когда комнат ещё нет."""

    add_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("emptyRoomsState")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel("📂")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 40px; background: transparent;")
        layout.addWidget(icon)

        title = QLabel("Пока нет комнат")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        hint = QLabel(
            "Выгрузите пакет комнаты (JSON) с сайта и добавьте его через кнопку ниже."
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        add_btn = QPushButton("Добавить комнату")
        add_btn.setObjectName("cta")
        add_btn.clicked.connect(self.add_clicked.emit)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


class HomeWidget(QWidget):
    open_room = pyqtSignal(str)
    rooms_changed = pyqtSignal()

    def __init__(self, storage: Storage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.storage = storage
        self._all_rooms: list[RegisteredRoomRow] = []
        self._package_ui_cache: dict[str, RoomCardMeta] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Тестирование")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.subtitle = QLabel(
            "Добавьте пакет комнаты (JSON с сайта), чтобы начать прохождение."
        )
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)

        section_row = QHBoxLayout()
        section = QLabel("Добавленные комнаты")
        section.setObjectName("sectionTitle")
        section_row.addWidget(section)
        section_row.addStretch()
        self.add_btn = QPushButton("+ Добавить комнату")
        self.add_btn.setObjectName("secondaryCta")
        self.add_btn.clicked.connect(self._on_add_room)
        section_row.addWidget(self.add_btn)
        layout.addLayout(section_row)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по названию…")
        self.search_edit.textChanged.connect(self._rebuild_room_cards)
        self.search_edit.hide()
        layout.addWidget(self.search_edit)

        self.empty_state = _EmptyRoomsState()
        self.empty_state.add_clicked.connect(self._on_add_room)
        layout.addWidget(self.empty_state, stretch=1)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.hide()
        self.rooms_container = QWidget()
        self.rooms_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        self.rooms_layout = QVBoxLayout(self.rooms_container)
        self.rooms_layout.setContentsMargins(0, 0, 0, 0)
        self.rooms_layout.setSpacing(8)
        self.rooms_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        # Без addStretch внизу — иначе карточки прижимаются кверху с серой дырой
        self.scroll.setWidget(self.rooms_container)
        layout.addWidget(self.scroll, stretch=1)

        self.refresh()

    def refresh(self) -> None:
        self._all_rooms = self.storage.list_registered_rooms()
        self._package_ui_cache.clear()
        has_rooms = len(self._all_rooms) > 0
        self.empty_state.setVisible(not has_rooms)
        self.scroll.setVisible(has_rooms)
        self.subtitle.setVisible(not has_rooms)
        self.search_edit.setVisible(len(self._all_rooms) >= 3)
        if not self.search_edit.isVisible():
            self.search_edit.clear()
        self._rebuild_room_cards()

    def _package_ui_for(self, row: RegisteredRoomRow) -> RoomCardMeta:
        """Мета карточки из пакета комнаты (кеш по room_public_id)."""
        if row.room_public_id in self._package_ui_cache:
            return self._package_ui_cache[row.room_public_id]
        package = None
        if row.package_exists:
            try:
                package = self.storage.load_package_for_room(row.room_public_id)
            except RoomPackageError:
                pass
        result = build_room_card_meta(
            package,
            tested_participant_count=row.participant_count,
        )
        self._package_ui_cache[row.room_public_id] = result
        return result

    def _filtered_rooms(self) -> list[RegisteredRoomRow]:
        query = self.search_edit.text().strip().casefold()
        if not query:
            return self._all_rooms
        result: list[RegisteredRoomRow] = []
        for row in self._all_rooms:
            hay = f"{row.quiz_title} {row.room_name}".casefold()
            if query in hay:
                result.append(row)
        return result

    def _clear_room_cards(self) -> None:
        while self.rooms_layout.count():
            item = self.rooms_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _rebuild_room_cards(self) -> None:
        if not self._all_rooms:
            self._clear_room_cards()
            return
        self._clear_room_cards()
        for row in self._filtered_rooms():
            meta = self._package_ui_for(row)
            card = RoomCard(
                row,
                quiz_kind=meta.quiz_kind,
                badge_labels=meta.home_badges,
            )
            card.enter_clicked.connect(self.open_room.emit)
            card.update_requested.connect(self._on_update_room)
            self.rooms_layout.addWidget(card)

    def _pick_json_file(self, title: str) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            "",
            "JSON (*.json)",
        )
        if not path:
            return None
        return Path(path)

    def _on_add_room(self) -> None:
        path = self._pick_json_file("Выберите пакет комнаты")
        if path is None:
            return
        try:
            self.storage.register_room_from_file(path, update_if_exists=False)
        except RoomPackageError as exc:
            if "уже добавлена" in str(exc).lower():
                if ask_yes_no(
                    self,
                    "Комната уже есть",
                    f"{exc}\n\nОбновить пакет из выбранного файла?",
                ):
                    try:
                        self.storage.register_room_from_file(
                            path,
                            update_if_exists=True,
                        )
                    except RoomPackageError as inner:
                        QMessageBox.warning(self, "Ошибка", str(inner))
                        return
                else:
                    return
            else:
                QMessageBox.warning(self, "Ошибка", str(exc))
                return
        self.refresh()
        self.rooms_changed.emit()

    def _on_update_room(self, room_public_id: str) -> None:
        path = self._pick_json_file("Выберите новый пакет комнаты")
        if path is None:
            return
        try:
            self.storage.relink_room_package(room_public_id, path)
        except RoomPackageError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return
        self.refresh()
        self.rooms_changed.emit()
