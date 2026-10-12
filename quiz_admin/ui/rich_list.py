"""Делегат списка: заголовок + пояснение с переносом строк (без обрезания текста)."""

from __future__ import annotations

from html import escape

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAbstractTextDocumentLayout, QPalette, QTextDocument
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

from quiz_admin.ui.theme import TEXT, TEXT_SECONDARY

HTML_ROLE = Qt.ItemDataRole.UserRole + 10
_PAD_X = 14
_PAD_Y = 10


def rich_html(title: str, details: str = "", *, warn: bool = False) -> str:
    """HTML для строки списка: жирный заголовок и серая подпись."""
    color = "#B3261E" if warn else TEXT
    html = f"<div style='color:{color}; font-weight:600;'>{escape(title)}</div>"
    if details:
        html += (
            f"<div style='color:{TEXT_SECONDARY}; margin-top:3px;'>{escape(details)}</div>"
        )
    return html


class RichItemDelegate(QStyledItemDelegate):
    @staticmethod
    def _indent(option: QStyleOptionViewItem, index) -> int:
        """Отступ под чекбокс у отмечаемых элементов."""
        if index.data(Qt.ItemDataRole.CheckStateRole) is not None:
            return option.fontMetrics.height() + 28
        return 0

    def _document(self, option: QStyleOptionViewItem, index, width: int) -> QTextDocument:
        doc = QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setTextWidth(max(80, width - 2 * _PAD_X - self._indent(option, index)))
        html = index.data(HTML_ROLE)
        doc.setHtml(html if html else f"<div>{escape(str(index.data() or ''))}</div>")
        return doc

    def _width(self, option: QStyleOptionViewItem) -> int:
        widget = option.widget
        if isinstance(widget, QAbstractItemView):
            return widget.viewport().width() - 12
        return option.rect.width()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        width = self._width(option)
        doc = self._document(option, index, width)
        return QSize(width, int(doc.size().height()) + 2 * _PAD_Y)

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else None
        if style is not None:
            style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        doc = self._document(option, index, option.rect.width())
        painter.save()
        painter.translate(
            option.rect.left() + _PAD_X + self._indent(option, index),
            option.rect.top() + _PAD_Y,
        )
        ctx = QAbstractTextDocumentLayout.PaintContext()
        ctx.palette.setColor(QPalette.ColorRole.Text, option.palette.color(QPalette.ColorRole.Text))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()


class RichListWidget(QListWidget):
    """Список с переносом текста; высота строк пересчитывается при смене ширины."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setItemDelegate(RichItemDelegate(self))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSpacing(4)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrap(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.scheduleDelayedItemsLayout()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # минимум ~9 строк текста: список не схлопывается при крупном шрифте
        self.setMinimumHeight(self.fontMetrics().height() * 9)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # смена масштаба/шрифта → стили обновились, нужно пересчитать размеры строк
        self.scheduleDelayedItemsLayout()


def add_rich_item(
    widget: QListWidget, title: str, details: str = "", *, data=None, warn: bool = False
) -> QListWidgetItem:
    item = QListWidgetItem(f"{title}\n{details}" if details else title)
    item.setData(HTML_ROLE, rich_html(title, details, warn=warn))
    if data is not None:
        item.setData(Qt.ItemDataRole.UserRole, data)
    widget.addItem(item)
    return item


def update_rich_item(
    item: QListWidgetItem, title: str, details: str = "", *, warn: bool = False
) -> None:
    item.setText(f"{title}\n{details}" if details else title)
    item.setData(HTML_ROLE, rich_html(title, details, warn=warn))
