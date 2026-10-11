"""Оформление конструктора (палитра совпадает с плеером)."""

from __future__ import annotations

PRIMARY = "#5AA9E6"
PRIMARY_DARK = "#3e76a1"
PRIMARY_LIGHT = "#e5effc"
BACKGROUND = "#ffffff"
PAPER = "#f9f9f9"
TEXT = "#212121"
TEXT_SECONDARY = "#646464"
BORDER = "#dbdbdb"
ERROR = "#f44336"

FONT_FAMILY = '"Segoe UI", "Inter", sans-serif'


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: 14px;
        color: {TEXT};
    }}
    QMainWindow, QDialog {{ background: {BACKGROUND}; }}
    QLabel#pageTitle {{ font-size: 22px; font-weight: 600; }}
    QLabel#sectionTitle {{ font-size: 16px; font-weight: 600; }}
    QLabel#subtitle {{ color: {TEXT_SECONDARY}; }}
    QLabel#warn {{ color: {ERROR}; }}
    QPushButton {{
        background: {PAPER};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 7px 14px;
    }}
    QPushButton:hover {{ background: {PRIMARY_LIGHT}; }}
    QPushButton:disabled {{ color: {TEXT_SECONDARY}; background: {PAPER}; }}
    QPushButton#primary {{
        background: {PRIMARY};
        border: 1px solid {PRIMARY_DARK};
        color: #ffffff;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{ background: {PRIMARY_DARK}; }}
    QPushButton#danger {{ color: {ERROR}; }}
    QPushButton#back {{ font-size: 18px; padding: 0; }}
    QToolButton#removeOption {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        background: {PAPER};
        padding: 4px 8px;
    }}
    QListWidget {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        background: {BACKGROUND};
        outline: none;
    }}
    QListWidget::item {{ padding: 8px 10px; }}
    QListWidget::item:selected {{ background: {PRIMARY_LIGHT}; color: {TEXT}; }}
    QLineEdit, QPlainTextEdit, QSpinBox, QComboBox, QTableWidget {{
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 5px 8px;
        background: {BACKGROUND};
    }}
    QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 6px; top: -1px; }}
    QTabBar::tab {{ padding: 8px 18px; border: 1px solid transparent; }}
    QTabBar::tab:selected {{
        border: 1px solid {BORDER};
        border-bottom-color: {BACKGROUND};
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        background: {BACKGROUND};
    }}
    """
