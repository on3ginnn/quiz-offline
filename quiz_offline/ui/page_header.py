"""Шапка экрана: назад + заголовок + подзаголовок (+ опционально trailing)."""

from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


from quiz_offline.ui.meta_badges_row import MetaBadgesRow


class PageHeader(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        on_back: Callable[[], None] | None = None,
        back_tooltip: str = "Назад",
    ) -> None:
        super().__init__(parent)
        self._on_back = on_back

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.back_btn = QPushButton("←")
        self.back_btn.setObjectName("back")
        self.back_btn.setToolTip(back_tooltip)
        self.back_btn.setFixedSize(40, 40)
        self.back_btn.clicked.connect(self._handle_back)
        self.back_btn.setVisible(on_back is not None)
        row.addWidget(self.back_btn, alignment=Qt.AlignmentFlag.AlignTop)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        self.title_label = QLabel()
        self.title_label.setObjectName("pageTitle")
        self.title_label.setWordWrap(True)
        titles.addWidget(self.title_label)
        self.meta_badges = MetaBadgesRow()
        titles.addWidget(self.meta_badges)
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitle")
        self.subtitle_label.setWordWrap(True)
        titles.addWidget(self.subtitle_label)
        row.addLayout(titles, stretch=1)

        self.trailing_host = QWidget()
        self.trailing_layout = QHBoxLayout(self.trailing_host)
        self.trailing_layout.setContentsMargins(0, 0, 0, 0)
        self.trailing_layout.setSpacing(8)
        row.addWidget(self.trailing_host, alignment=Qt.AlignmentFlag.AlignTop)

    def _handle_back(self) -> None:
        if self._on_back is not None:
            self._on_back()

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def set_meta_badges(self, labels: list[str]) -> None:
        self.meta_badges.set_labels(labels)

    def set_trailing(self, widget: QWidget | None) -> None:
        while self.trailing_layout.count():
            item = self.trailing_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if widget is not None:
            self.trailing_layout.addWidget(widget)
