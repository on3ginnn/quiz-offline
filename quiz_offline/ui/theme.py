"""Дизайн-система плеера: токены, масштаб текста, QSS.

Структура модуля совпадает с ``quiz_admin/ui/theme.py`` — при изменении токенов
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
_SETTINGS_APP = "QuizOffline"
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
        path = Path(tempfile.gettempdir()) / "AlmetQuizOffline" / "check.png"
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
    QMainWindow, QDialog, QStackedWidget, QMessageBox {{
        background-color: {BACKGROUND};
    }}
    QLabel {{ background: transparent; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QToolTip {{
        background: {TEXT}; color: #ffffff; border: none; padding: {px(6)}px {px(8)}px;
        font-size: {px(14)}px;
    }}

    /* ---- Текст ---- */
    QLabel#pageTitle {{ font-size: {px(28)}px; font-weight: 700; }}
    QLabel#sectionTitle {{ font-size: {px(20)}px; font-weight: 600; }}
    QLabel#subtitle {{ color: {TEXT_SECONDARY}; font-size: {px(15)}px; }}
    QLabel#questionText {{
        font-size: {px(26)}px; font-weight: 600; padding: 0; margin: 0;
    }}
    QLabel#optionText {{ font-size: {px(19)}px; padding: 0; margin: 0; }}
    QLabel#timerBadge {{
        font-size: {px(20)}px; font-weight: 700; color: {PRIMARY};
        background: {PRIMARY_LIGHT}; padding: {px(8)}px {px(16)}px; border-radius: {px(10)}px;
    }}
    QLabel#timerBadge[urgent="true"] {{
        color: {ERROR}; background: {ERROR_LIGHT};
    }}
    QLabel#metaBadge {{
        background: {PRIMARY_LIGHT}; color: {PRIMARY};
        padding: {px(4)}px {px(10)}px; border-radius: {px(8)}px;
        font-size: {px(14)}px; font-weight: 600;
    }}
    QLabel#fieldError {{ color: {ERROR}; font-size: {px(14)}px; font-weight: 600; }}

    /* ---- Кнопки ---- */
    QPushButton {{
        padding: {px(10)}px {px(18)}px; border-radius: {px(8)}px;
        border: 1px solid {BORDER}; background: {SURFACE}; font-weight: 600;
        min-height: {px(22)}px;
    }}
    QPushButton:hover {{ background: {PRIMARY_LIGHT}; border-color: {PRIMARY}; }}
    QPushButton:pressed {{ background: {BORDER_SOFT}; }}
    QPushButton:focus {{ border: {px(3)}px solid {FOCUS}; }}
    QPushButton:disabled {{
        color: {DISABLED_TEXT}; background: {DISABLED_BG}; border-color: {BORDER_SOFT};
    }}
    QPushButton#primary, QPushButton#cta, QPushButton#roomEnterPrimary {{
        background: {PRIMARY}; color: #ffffff; border: 1px solid {PRIMARY};
        min-height: {px(26)}px; padding: {px(12)}px {px(22)}px;
    }}
    QPushButton#primary:hover, QPushButton#cta:hover, QPushButton#roomEnterPrimary:hover {{
        background: {PRIMARY_HOVER}; border-color: {PRIMARY_HOVER};
    }}
    QPushButton#primary:focus, QPushButton#cta:focus, QPushButton#roomEnterPrimary:focus {{
        border: {px(3)}px solid {FOCUS};
    }}
    QPushButton#primary:disabled, QPushButton#cta:disabled {{
        background: {DISABLED_BG}; color: {DISABLED_TEXT}; border-color: {BORDER_SOFT};
    }}
    QPushButton#secondaryCta {{
        background: {SURFACE}; color: {PRIMARY}; border: 2px solid {PRIMARY};
        min-height: {px(26)}px;
    }}
    QPushButton#secondaryCta:hover {{ background: {PRIMARY_LIGHT}; }}
    QPushButton#back {{
        border: 1px solid {BORDER}; background: {SURFACE}; font-size: {px(18)}px;
        padding: {px(6)}px {px(14)}px; min-height: {px(22)}px;
    }}
    QPushButton#textAction {{
        border: none; background: transparent; color: {PRIMARY};
        padding: {px(8)}px {px(12)}px;
    }}
    QPushButton#textAction:hover {{ background: {PRIMARY_LIGHT}; }}
    QPushButton#navIcon, QPushButton#takingFooterBtn, QPushButton#resultBtn {{
        min-height: {px(26)}px; padding: {px(12)}px {px(20)}px;
    }}
    QPushButton#resultBtn {{ min-width: {px(168)}px; }}
    QPushButton#scaleBtn {{
        padding: {px(4)}px {px(10)}px; min-height: {px(20)}px; min-width: {px(20)}px;
        font-size: {px(15)}px;
    }}
    QToolButton#roomMenuBtn {{
        border: 1px solid {BORDER}; background: {SURFACE}; font-size: {px(20)}px;
        font-weight: 700; border-radius: {px(8)}px;
        min-width: {px(44)}px; max-width: {px(44)}px;
        min-height: {px(44)}px; max-height: {px(44)}px; padding: 0;
    }}
    QToolButton#roomMenuBtn:hover {{ background: {PRIMARY_LIGHT}; border-color: {PRIMARY}; }}
    QToolButton#roomMenuBtn:focus {{ border: {px(3)}px solid {FOCUS}; }}
    QToolButton#roomMenuBtn::menu-indicator {{ image: none; width: 0; }}
    QMenu {{
        padding: {px(6)}px 0; border: 1px solid {BORDER}; background: {SURFACE};
    }}
    QMenu::item {{ padding: {px(10)}px {px(22)}px; min-height: {px(22)}px; }}
    QMenu::item:selected {{ background: {PRIMARY_LIGHT}; color: {TEXT}; }}

    /* ---- Карточки ---- */
    QFrame#roomCard, QFrame#questionCard, QFrame#metricTile, QFrame#resultCard {{
        background: {SURFACE}; border: 1px solid {BORDER_SOFT}; border-radius: {px(14)}px;
    }}
    QFrame#roomCard:hover {{ border: 2px solid {PRIMARY}; }}
    QFrame#roomCardIconBadge {{
        background: {PRIMARY_LIGHT}; border-radius: {px(12)}px; border: none;
    }}
    QLabel#roomCardHeading {{ font-size: {px(18)}px; font-weight: 700; }}
    QLabel#roomCardIcon {{ font-size: {px(26)}px; }}
    QLabel#roomCardMeta, QLabel#roomCardActivity {{
        font-size: {px(15)}px; color: {TEXT_SECONDARY};
    }}
    QLabel#roomCardStat {{ font-size: {px(15)}px; color: {TEXT_SECONDARY}; font-weight: 600; }}
    QLabel#roomCardWarn {{ font-size: {px(14)}px; color: {ERROR}; font-weight: 600; }}
    QWidget#emptyRoomsState {{
        background: {SURFACE}; border: 2px dashed {BORDER}; border-radius: {px(16)}px;
    }}
    QFrame#optionCard {{
        background: {SURFACE}; border: 2px solid {BORDER_SOFT}; border-radius: {px(12)}px;
    }}
    QFrame#optionCard:hover {{ border-color: {PRIMARY}; }}
    QFrame#optionCard[selected="true"] {{
        border: 2px solid {PRIMARY}; background: {PRIMARY_LIGHT};
    }}
    QFrame#optionCard[focused="true"] {{ border: {px(3)}px solid {FOCUS}; }}
    QFrame#resultCard[tone="fail"] {{ background: #FCEAE8; border: 2px solid #B3261E; }}
    QFrame#resultCard[tone="warn"] {{ background: #FFF3E0; border: 2px solid #9A5200; }}
    QFrame#resultCard[tone="ok"] {{ background: #E6F4EA; border: 2px solid #1E7B45; }}
    QLabel#gradeResult[tone="fail"], QLabel#resultMetricValue[tone="fail"] {{ color: #B3261E; }}
    QLabel#gradeResult[tone="warn"], QLabel#resultMetricValue[tone="warn"] {{ color: #9A5200; }}
    QLabel#gradeResult[tone="ok"], QLabel#resultMetricValue[tone="ok"] {{ color: #1E7B45; }}
    QLabel#gradeResult {{ font-size: {px(34)}px; font-weight: 700; }}
    QLabel#resultPercentCaption {{ font-size: {px(16)}px; }}
    QLabel#resultMetricValue {{ font-size: {px(24)}px; font-weight: 700; }}

    /* ---- Выбор ответа ---- */
    QRadioButton, QCheckBox {{
        font-size: {px(19)}px; spacing: {px(12)}px; padding: {px(6)}px 0;
    }}
    QRadioButton::indicator, QCheckBox::indicator {{
        width: {px(22)}px; height: {px(22)}px;
    }}
    QRadioButton::indicator {{
        border: 2px solid {BORDER}; border-radius: {px(13)}px; background: {SURFACE};
    }}
    QRadioButton::indicator:checked {{
        border: {px(7)}px solid {PRIMARY}; background: {SURFACE};
    }}
    QCheckBox::indicator {{
        border: 2px solid {BORDER}; border-radius: {px(5)}px; background: {SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {PRIMARY}; border-color: {PRIMARY}; {check_image}
    }}
    QRadioButton:focus, QCheckBox:focus {{ outline: none; }}

    /* ---- Списки, таблицы, поля ---- */
    QListWidget {{
        border: 1px solid {BORDER_SOFT}; border-radius: {px(12)}px;
        background: {SURFACE}; padding: {px(6)}px; outline: none;
    }}
    QListWidget::item {{ padding: {px(12)}px; border-radius: {px(8)}px; }}
    QListWidget::item:selected {{ background: {PRIMARY_LIGHT}; color: {TEXT}; }}
    QTableWidget {{
        border: 1px solid {BORDER_SOFT}; border-radius: {px(12)}px;
        gridline-color: {BORDER_SOFT}; background: {SURFACE};
        alternate-background-color: {BACKGROUND}; selection-background-color: {PRIMARY_LIGHT};
        selection-color: {TEXT};
    }}
    QTableWidget::item {{ padding: {px(8)}px; }}
    QHeaderView::section {{
        background: {PRIMARY_LIGHT}; color: {TEXT}; padding: {px(10)}px;
        border: none; border-bottom: 1px solid {BORDER}; font-weight: 700;
    }}
    QLineEdit {{
        padding: {px(10)}px {px(12)}px; border: 1px solid {BORDER};
        border-radius: {px(8)}px; background: {SURFACE};
        min-height: {px(22)}px; selection-background-color: {PRIMARY};
        selection-color: #ffffff;
    }}
    QLineEdit:focus {{ border: {px(3)}px solid {FOCUS}; }}
    QGroupBox {{
        border: 1px solid {BORDER_SOFT}; border-radius: {px(12)}px;
        margin-top: {px(12)}px; padding: {px(12)}px; background: {SURFACE};
    }}
    QScrollBar:vertical {{ background: transparent; width: {px(14)}px; margin: 0; }}
    QScrollBar::handle:vertical {{
        background: {BORDER}; border-radius: {px(6)}px; min-height: {px(40)}px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {TEXT_SECONDARY}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QProgressBar {{
        border: none; border-radius: {px(5)}px; background: {BORDER_SOFT};
        max-height: {px(10)}px; min-height: {px(10)}px; text-align: center;
    }}
    QProgressBar::chunk {{ background: {PRIMARY}; border-radius: {px(5)}px; }}
    """
