"""Диалоги с русскими подписями кнопок."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox, QWidget


def ask_yes_no(parent: QWidget | None, title: str, text: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    yes_btn = box.addButton("Да", QMessageBox.ButtonRole.YesRole)
    no_btn = box.addButton("Нет", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(yes_btn)
    box.exec()
    return box.clickedButton() == yes_btn
