"""Точка входа Quiz Offline."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from quiz_offline.storage import Storage
from quiz_offline.ui.main_window import MainWindow
from quiz_offline.ui.theme import app_stylesheet, install_russian_translations, load_scale


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Quiz Offline")
    install_russian_translations(app)
    app.setStyleSheet(app_stylesheet(load_scale()))
    storage = Storage()
    window = MainWindow(storage)
    window.show()
    code = app.exec()
    storage.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
