"""Точка входа Quiz Admin."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from quiz_admin.storage import AdminStorage
from quiz_admin.ui.main_window import MainWindow
from quiz_admin.ui.theme import app_stylesheet, install_russian_translations, load_scale


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Quiz Admin")
    install_russian_translations(app)
    app.setStyleSheet(app_stylesheet(load_scale()))
    storage = AdminStorage()
    window = MainWindow(storage)
    window.show()
    code = app.exec()
    storage.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
