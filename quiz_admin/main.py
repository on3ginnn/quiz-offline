"""Точка входа Quiz Admin."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from quiz_admin.storage import AdminStorage
from quiz_admin.ui.main_window import MainWindow
from quiz_admin.ui.theme import app_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Quiz Admin")
    app.setStyleSheet(app_stylesheet())
    storage = AdminStorage()
    window = MainWindow(storage)
    window.show()
    code = app.exec()
    storage.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
