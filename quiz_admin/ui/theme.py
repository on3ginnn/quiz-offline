"""Дизайн-система конструктора: токены, масштаб текста, QSS.

Структура модуля совпадает с ``quiz_offline/ui/theme.py`` — при изменении токенов
и общих стилей правьте оба файла (у приложений нет общего кода).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PyQt6.QtCore import QLibraryInfo, QLocale, QPointF, QSettings, Qt, QTranslator
from PyQt6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QApplication

# --- Палитра (контраст текста ≥ 4.5:1, границ/иконок ≥ 3:1) ---
PRIMARY = "#1F6FB5"
PRIMARY_HOVER = "#185A94"
PRIMARY_LIGHT = "#E6F0FA"
ACCENT = "#5AA9E6"
BACKGROUND = "#F4F7FB"
SURFACE = "#FFFFFF"
TEXT = "#1B2430"
TEXT_SECONDARY = "#4B5766"
BORDER = "#B7C2CF"
BORDER_SOFT = "#D9E0E8"
FOCUS = "#0B57A4"
SUCCESS = "#1E7B45"
WARNING = "#B35C00"
ERROR = "#B3261E"
ERROR_LIGHT = "#FCEAE8"
DISABLED_BG = "#E3E8EE"
DISABLED_TEXT = "#6B7684"

FONT_FAMILY = '"Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif'

# --- Масштаб текста (режим для слабовидящих) ---
SCALES = (1.0, 1.25, 1.5, 2.0)
DEFAULT_SCALE = 1.0
_SETTINGS_ORG = "AlmetQuiz"
_SETTINGS_APP = "QuizAdmin"
_SETTINGS_KEY = "ui/text_scale"

MAX_CONTENT_WIDTH = 1100


def clamp_scale(value: float) -> float:
    """Ближайшее допустимое значение масштаба."""
    return min(SCALES, key=lambda s: abs(s - float(value)))


def next_scale(current: float, step: int) -> float:
    idx = SCALES.index(clamp_scale(current)) + step
    return SCALES[max(0, min(len(SCALES) - 1, idx))]


def load_scale() -> float:
    try:
        raw = QSettings(_SETTINGS_ORG, _SETTINGS_APP).value(_SETTINGS_KEY, DEFAULT_SCALE)
        return clamp_scale(float(raw))
    except (TypeError, ValueError):
        return DEFAULT_SCALE


def save_scale(scale: float) -> None:
    QSettings(_SETTINGS_ORG, _SETTINGS_APP).setValue(_SETTINGS_KEY, clamp_scale(scale))


def install_russian_translations(app: QApplication) -> None:
    """Русские подписи стандартных кнопок Qt (ОК/Отмена/Да/Нет, диалоги файлов)."""
    QLocale.setDefault(QLocale(QLocale.Language.Russian, QLocale.Country.Russia))
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in ("qtbase_ru", "qt_ru"):
        translator = QTranslator(app)
        if translator.load(name, path):
            app.installTranslator(translator)


def _check_icon_url() -> str:
    """Белая «галочка» для чекбоксов (QSS не умеет рисовать её сам). Пустая строка при сбое."""
    try:
        path = Path(tempfile.gettempdir()) / "AlmetQuizAdmin" / "check.png"
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            image = QImage(48, 48, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#FFFFFF"), 6)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPolyline(
                QPolygonF([QPointF(11, 25), QPointF(20, 34), QPointF(37, 14)])
            )
            painter.end()
            image.save(str(path))
        return path.as_posix()
    except Exception:
        return ""


def app_stylesheet(scale: float = DEFAULT_SCALE) -> str:
    def px(base: float) -> int:
        return max(1, round(base * scale))

    check_icon = _check_icon_url()
    check_image = f"image: url({check_icon});" if check_icon else ""

    return f"""
    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: {px(16)}px;
        color: {TEXT};
    }}
    QMainWindow, QDialog, QStackedWidget, QMessageBox {{ background: {BACKGROUND}; }}
    QLabel {{ background: transparent; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QToolTip {{
        background: {TEXT}; color: #ffffff; border: none; padding: {px(6)}px {px(8)}px;
        font-size: {px(14)}px;
    }}

    /* ---- Текст ---- */
    QLabel#pageTitle {{ font-size: {px(28)}px; font-weight: 700; }}
    QLabel#sectionTitle {{ font-size: {px(18)}px; font-weight: 700; }}
    QLabel#subtitle {{ color: {TEXT_SECONDARY}; font-size: {px(15)}px; }}
    QLabel#hint {{ color: {TEXT_SECONDARY}; font-size: {px(14)}px; }}
    QLabel#warn {{ color: {ERROR}; font-weight: 600; }}
    QLabel#emptyState {{
        color: {TEXT_SECONDARY}; font-size: {px(17)}px; padding: {px(40)}px;
        background: {SURFACE}; border: 2px dashed {BORDER}; border-radius: {px(14)}px;
    }}

    /* ---- Кнопки ---- */
    QPushButton {{
        background: {SURFACE}; border: 1px solid {BORDER}; border-radius: {px(8)}px;
        padding: {px(9)}px {px(16)}px; font-weight: 600; min-height: {px(22)}px;
    }}
    QPushButton:hover {{ background: {PRIMARY_LIGHT}; border-color: {PRIMARY}; }}
    QPushButton:pressed {{ background: {BORDER_SOFT}; }}
    QPushButton:focus {{ border: {px(3)}px solid {FOCUS}; }}
    QPushButton:disabled {{
        color: {DISABLED_TEXT}; background: {DISABLED_BG}; border-color: {BORDER_SOFT};
    }}
    QPushButton#primary {{
        background: {PRIMARY}; border: 1px solid {PRIMARY}; color: #ffffff;
        padding: {px(10)}px {px(20)}px;
    }}
    QPushButton#primary:hover {{ background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER}; }}
    QPushButton#primary:focus {{ border: {px(3)}px solid {FOCUS}; }}
    QPushButton#primary:disabled {{
        background: {DISABLED_BG}; color: {DISABLED_TEXT}; border-color: {BORDER_SOFT};
    }}
    QPushButton#danger {{ color: {ERROR}; border-color: {ERROR}; }}
    QPushButton#danger:hover {{ background: {ERROR_LIGHT}; }}
    QPushButton#danger:disabled {{
        color: {DISABLED_TEXT}; background: {DISABLED_BG}; border-color: {BORDER_SOFT};
    }}
    QPushButton#back {{ font-size: {px(16)}px; }}
    QPushButton#scaleBtn {{
        padding: {px(4)}px {px(10)}px; min-height: {px(20)}px; min-width: {px(20)}px;
        font-size: {px(15)}px;
    }}
    QToolButton#removeOption {{
        border: 1px solid {BORDER}; border-radius: {px(8)}px; background: {SURFACE};
        padding: {px(6)}px {px(10)}px; font-weight: 700; color: {ERROR};
    }}
    QToolButton#removeOption:hover {{ background: {ERROR_LIGHT}; border-color: {ERROR}; }}
    QToolButton#removeOption:focus {{ border: {px(3)}px solid {FOCUS}; }}

    /* ---- Карточки и разделы ---- */
    QFrame#card {{
        background: {SURFACE}; border: 1px solid {BORDER_SOFT}; border-radius: {px(14)}px;
    }}

    /* ---- Списки ---- */
    QListWidget {{
        border: 1px solid {BORDER_SOFT}; border-radius: {px(12)}px;
        background: {SURFACE}; padding: {px(6)}px; outline: none;
    }}
    QListWidget::item {{ border-radius: {px(8)}px; }}
    QListWidget::item:hover {{ background: {BACKGROUND}; }}
    QListWidget::item:selected {{
        background: {PRIMARY_LIGHT}; color: {TEXT}; border: 2px solid {PRIMARY};
    }}

    /* ---- Поля ввода ---- */
    QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
        border: 1px solid {BORDER}; border-radius: {px(8)}px;
        padding: {px(8)}px {px(10)}px; background: {SURFACE};
        selection-background-color: {PRIMARY}; selection-color: #ffffff;
    }}
    QLineEdit, QSpinBox, QComboBox {{ min-height: {px(24)}px; }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: {px(3)}px solid {FOCUS};
    }}
    QLineEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
        background: {DISABLED_BG}; color: {DISABLED_TEXT};
    }}
    QSpinBox {{ padding-right: {px(6)}px; min-width: {px(110)}px; }}
    QComboBox {{ padding-right: {px(28)}px; }}
    QComboBox QAbstractItemView {{
        border: 1px solid {BORDER}; background: {SURFACE};
        selection-background-color: {PRIMARY_LIGHT}; selection-color: {TEXT};
        padding: {px(4)}px;
    }}
    QCheckBox {{ spacing: {px(10)}px; padding: {px(4)}px 0; }}
    QCheckBox::indicator {{
        width: {px(22)}px; height: {px(22)}px;
        border: 2px solid {BORDER}; border-radius: {px(5)}px; background: {SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {PRIMARY}; border-color: {PRIMARY}; {check_image}
    }}
    QCheckBox::indicator:disabled {{ background: {DISABLED_BG}; }}
    QCheckBox:focus {{ color: {FOCUS}; }}

    /* ---- Таблицы, вкладки, меню ---- */
    QTableWidget {{
        border: 1px solid {BORDER_SOFT}; border-radius: {px(12)}px;
        gridline-color: {BORDER_SOFT}; background: {SURFACE};
        alternate-background-color: {BACKGROUND};
    }}
    QTableWidget::item {{ padding: {px(6)}px; }}
    QHeaderView::section {{
        background: {PRIMARY_LIGHT}; color: {TEXT}; padding: {px(10)}px;
        border: none; border-bottom: 1px solid {BORDER}; font-weight: 700;
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER_SOFT}; border-radius: {px(12)}px;
        background: {SURFACE}; top: -1px;
    }}
    QTabBar::tab {{
        padding: {px(12)}px {px(22)}px; border: 1px solid transparent;
        font-weight: 600; color: {TEXT_SECONDARY};
    }}
    QTabBar::tab:hover {{ color: {TEXT}; }}
    QTabBar::tab:selected {{
        border: 1px solid {BORDER_SOFT}; border-bottom-color: {SURFACE};
        border-top-left-radius: {px(10)}px; border-top-right-radius: {px(10)}px;
        background: {SURFACE}; color: {PRIMARY};
    }}
    QSplitter::handle {{ background: transparent; }}
    QMenu {{ padding: {px(6)}px 0; border: 1px solid {BORDER}; background: {SURFACE}; }}
    QMenu::item {{ padding: {px(10)}px {px(22)}px; }}
    QMenu::item:selected {{ background: {PRIMARY_LIGHT}; color: {TEXT}; }}
    QScrollBar:vertical {{ background: transparent; width: {px(14)}px; margin: 0; }}
    QScrollBar::handle:vertical {{
        background: {BORDER}; border-radius: {px(6)}px; min-height: {px(40)}px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_SECONDARY}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    """
