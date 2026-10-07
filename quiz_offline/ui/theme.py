"""Стили PyQt в духе MUI-темы сайта."""

from pathlib import Path

from PyQt6.QtGui import QFontDatabase

PRIMARY = "#5AA9E6"
PRIMARY_DARK = "#3e76a1"
PRIMARY_LIGHT = "#e5effc"
BACKGROUND = "#ffffff"
PAPER = "#f9f9f9"
TEXT = "#212121"
TEXT_SECONDARY = "#646464"
BORDER = "#dbdbdb"
SUCCESS = "#30AD6F"
WARNING = "#FFC107"
ERROR = "#f44336"

FONT_FAMILY = '"Inter", "Segoe UI", sans-serif'

# Экран прохождения: база ×1.5, затем −20% → ×1.2 от исходных 21/15
QUESTION_FONT_PX = 26
OPTION_FONT_PX = 18
FOOTER_BTN_MIN_HEIGHT = 40


def try_load_inter_font() -> None:
    """Подключает Inter из assets фронтенда, если файл доступен."""
    repo_root = Path(__file__).resolve().parents[3]
    font_path = (
        repo_root
        / "frontend"
        / "src"
        / "assets"
        / "fonts"
        / "inter"
        / "Inter-VariableFont_opsz,wght.ttf"
    )
    if font_path.is_file():
        QFontDatabase.addApplicationFont(str(font_path))


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        font-family: {FONT_FAMILY};
        font-size: 14px;
        color: {TEXT};
        background-color: {BACKGROUND};
    }}
    QLabel {{
        background: transparent;
    }}
    QMainWindow {{
        background-color: {BACKGROUND};
    }}
    QLabel#pageTitle {{
        font-size: 22px;
        font-weight: 600;
    }}
    QLabel#sectionTitle {{
        font-size: 15px;
        font-weight: 600;
        color: {TEXT};
    }}
    QLabel#subtitle {{
        color: {TEXT_SECONDARY};
        font-size: 13px;
    }}
    QLabel#questionText {{
        font-size: {QUESTION_FONT_PX}px;
        font-weight: 600;
        color: {TEXT};
        background: transparent;
        padding: 0;
        margin: 0;
    }}
    QLabel#timerBadge {{
        font-size: 18px;
        font-weight: 600;
        color: {PRIMARY_DARK};
        background: {PRIMARY_LIGHT};
        padding: 8px 14px;
        border-radius: 8px;
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QFrame#questionCard {{
        background: transparent;
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    QScrollArea#questionScroll {{
        background: transparent;
        border: none;
    }}
    QScrollArea#questionScroll > QWidget > QWidget {{
        background: transparent;
    }}
    QRadioButton, QCheckBox {{
        font-size: {OPTION_FONT_PX}px;
        spacing: 10px;
        padding: 4px 0;
        background: transparent;
    }}
    QLabel#optionText {{
        font-size: {OPTION_FONT_PX}px;
        background: transparent;
        padding: 0;
        margin: 0;
    }}
    QPushButton {{
        padding: 8px 16px;
        border-radius: 6px;
        border: 1px solid {BORDER};
        background: {BACKGROUND};
    }}
    QPushButton:hover {{
        background: {PAPER};
    }}
    QPushButton#primary {{
        background: {PRIMARY};
        color: white;
        border: none;
        font-weight: 600;
        min-height: {FOOTER_BTN_MIN_HEIGHT}px;
        padding: 8px 16px;
    }}
    QPushButton#primary:hover {{
        background: {PRIMARY_DARK};
    }}
    QPushButton#primary:disabled {{
        background: #b0cfe8;
    }}
    QPushButton#navIcon {{
        min-height: {FOOTER_BTN_MIN_HEIGHT}px;
        min-width: {FOOTER_BTN_MIN_HEIGHT}px;
        padding: 8px;
        border: 1px solid {BORDER};
        background: {BACKGROUND};
        border-radius: 6px;
    }}
    QPushButton#takingFooterBtn {{
        min-height: {FOOTER_BTN_MIN_HEIGHT}px;
        padding: 8px 16px;
    }}
    QPushButton#navIcon:hover {{
        background: {PAPER};
        border-color: {PRIMARY};
    }}
    QPushButton#navIcon:disabled {{
        color: {TEXT_SECONDARY};
        background: #f5f5f5;
    }}
    QPushButton#cta {{
        background: {PRIMARY};
        color: white;
        border: none;
        font-weight: 600;
        min-height: 44px;
        padding: 10px 16px;
    }}
    QPushButton#cta:hover {{
        background: {PRIMARY_DARK};
    }}
    QPushButton#cta:disabled {{
        background: #b0cfe8;
    }}
    QPushButton#back {{
        border: none;
        background: transparent;
        font-size: 20px;
        font-weight: 600;
        color: {TEXT};
        padding: 0;
    }}
    QPushButton#back:hover {{
        background: {PAPER};
        border-radius: 8px;
    }}
    QPushButton#textAction {{
        border: none;
        background: transparent;
        color: {PRIMARY_DARK};
        font-weight: 600;
        padding: 6px 10px;
    }}
    QPushButton#textAction:hover {{
        background: {PRIMARY_LIGHT};
        border-radius: 6px;
    }}
    QPushButton#secondaryCta {{
        background: {BACKGROUND};
        color: {PRIMARY_DARK};
        border: 1px solid {PRIMARY};
        font-weight: 600;
        padding: 6px 14px;
        min-height: 32px;
    }}
    QPushButton#secondaryCta:hover {{
        background: {PRIMARY_LIGHT};
    }}
    QPushButton#roomEnterPrimary {{
        background: {PRIMARY};
        color: white;
        border: none;
        font-weight: 600;
        padding: 8px 16px;
        min-height: 36px;
        border-radius: 6px;
    }}
    QPushButton#roomEnterPrimary:hover {{
        background: {PRIMARY_DARK};
    }}
    QToolButton#roomMenuBtn {{
        border: 1px solid {BORDER};
        background: #f5f5f5;
        padding: 0;
        font-size: 20px;
        font-weight: 700;
        color: {TEXT};
        border-radius: 8px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
    }}
    QToolButton#roomMenuBtn:hover {{
        background: {PRIMARY_LIGHT};
        border-color: {PRIMARY};
    }}
    QToolButton#roomMenuBtn::menu-indicator {{
        image: none;
        width: 0;
    }}
    QMenu#roomCardMenu {{
        padding: 6px 0;
        border: 1px solid {BORDER};
        border-radius: 8px;
        background: {PAPER};
    }}
    QMenu#roomCardMenu::item {{
        padding: 10px 18px;
        min-height: 20px;
        font-size: 14px;
    }}
    QMenu#roomCardMenu::item:selected {{
        background: {PRIMARY_LIGHT};
        color: {TEXT};
    }}
    QLabel#metaBadge {{
        background: {PRIMARY_LIGHT};
        color: {PRIMARY_DARK};
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
    }}
    QFrame#roomCard {{
        background: #fafafa;
        border: 1px solid #d6d6d6;
        border-radius: 10px;
    }}
    QFrame#roomCard:hover {{
        border-color: {PRIMARY};
        background: #f5f9ff;
    }}
    QFrame#roomCardIconBadge {{
        background: {PRIMARY_LIGHT};
        border-radius: 10px;
        border: none;
    }}
    QLabel#roomCardHeading {{
        font-size: 16px;
        font-weight: 600;
        color: {TEXT};
    }}
    QLabel#roomCardTitle {{
        font-size: 16px;
        font-weight: 600;
    }}
    QLabel#roomCardMeta {{
        font-size: 13px;
        color: {TEXT_SECONDARY};
    }}
    QLabel#roomCardStat {{
        font-size: 13px;
        color: {TEXT_SECONDARY};
        font-weight: 600;
        background: transparent;
    }}
    QLabel#roomCardActivity {{
        font-size: 13px;
        color: {TEXT_SECONDARY};
        background: transparent;
    }}
    QLabel#roomCardWarn {{
        font-size: 12px;
        color: {ERROR};
        font-weight: 600;
        background: transparent;
    }}
    QLabel#roomCardIcon {{
        font-size: 24px;
        background: transparent;
    }}
    QWidget#emptyRoomsState {{
        background: {PAPER};
        border: 1px dashed {BORDER};
        border-radius: 12px;
        padding: 24px;
    }}
    QFrame#metricTile {{
        background: transparent;
        border: 1px solid {BORDER};
        border-radius: 8px;
    }}
    QLabel#gradeResult {{
        font-size: 28px;
        font-weight: 700;
        background: transparent;
    }}
    QLabel#resultPercentCaption {{
        font-size: 15px;
        background: transparent;
    }}
    QLabel#resultMetricValue {{
        font-size: 22px;
        font-weight: 600;
        background: transparent;
    }}
    QPushButton#resultBtn {{
        background: {BACKGROUND};
        color: {TEXT};
        border: 1px solid {BORDER};
        font-weight: 600;
        min-height: 40px;
        min-width: 148px;
        padding: 8px 16px;
        border-radius: 6px;
    }}
    QPushButton#resultBtn:hover {{
        background: {PAPER};
        border-color: {PRIMARY};
    }}
    QPushButton#resultBtn:disabled {{
        color: {TEXT_SECONDARY};
        background: #f5f5f5;
    }}
    QListWidget {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        background: {PAPER};
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 12px;
        border-radius: 6px;
    }}
    QListWidget::item:selected {{
        background: {PRIMARY_LIGHT};
        color: {TEXT};
    }}
    QTableWidget {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        gridline-color: {BORDER};
        background: {PAPER};
    }}
    QHeaderView::section {{
        background: #f5f5f5;
        padding: 8px;
        border: none;
        border-bottom: 1px solid {BORDER};
        font-weight: 600;
        font-size: 13px;
    }}
    QLineEdit {{
        padding: 10px 12px;
        border: 1px solid {BORDER};
        border-radius: 6px;
        background: {BACKGROUND};
    }}
    QLineEdit:focus {{
        border: 2px solid {PRIMARY};
    }}
    QGroupBox {{
        border: 1px solid {BORDER};
        border-radius: 8px;
        margin-top: 12px;
        padding: 12px;
        background: {PAPER};
    }}
  """
