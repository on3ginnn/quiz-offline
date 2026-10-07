"""Точка входа Quiz Offline."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from quiz_offline.storage import Storage
from quiz_offline.ui.main_window import MainWindow
from quiz_offline.ui.theme import app_stylesheet, try_load_inter_font


def main() -> int:
    app = QApplication(sys.argv)
    try_load_inter_font()
    app.setApplicationName("Quiz Offline")
    app.setStyleSheet(app_stylesheet())
    storage = Storage()
    window = MainWindow(storage)
    window.show()
    code = app.exec()
    storage.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
