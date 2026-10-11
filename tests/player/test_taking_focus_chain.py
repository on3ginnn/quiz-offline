"""Тесты цепочки клавиатурного фокуса на экране прохождения."""

from __future__ import annotations

from unittest.mock import Mock

from PyQt6.QtCore import Qt

from quiz_offline.ui.taking_keyboard import (
    build_taking_focus_chain,
    is_widget_focusable,
    move_focus_in_chain,
)


def _mock_widget(
    *,
    visible: bool = True,
    enabled: bool = True,
    no_focus: bool = False,
) -> Mock:
    widget = Mock()
    widget.isVisible.return_value = visible
    widget.isEnabled.return_value = enabled
    widget.focusPolicy.return_value = (
        Qt.FocusPolicy.NoFocus
        if no_focus
        else Qt.FocusPolicy.StrongFocus
    )
    return widget


def test_build_taking_focus_chain_order():
    opt1 = _mock_widget()
    opt2 = _mock_widget()
    next_btn = _mock_widget()
    prev_btn = _mock_widget(enabled=False)
    clear_btn = _mock_widget(visible=False)

    chain = build_taking_focus_chain(
        [opt1, opt2],
        next_btn,
        prev_btn,
        clear_btn,
    )
    assert chain == [opt1, opt2, next_btn]


def test_move_focus_in_chain_cycles():
    opt1 = _mock_widget()
    opt2 = _mock_widget()
    next_btn = _mock_widget()
    chain = [opt1, opt2, next_btn]

    moved = move_focus_in_chain(chain, opt1, 1)
    assert moved is opt2
    opt2.setFocus.assert_called_once()

    moved = move_focus_in_chain(chain, opt2, 1)
    assert moved is next_btn
    next_btn.setFocus.assert_called_once()

    moved = move_focus_in_chain(chain, next_btn, 1)
    assert moved is opt1
    opt1.setFocus.assert_called_once()


def test_is_widget_focusable_skips_hidden_and_disabled():
    assert not is_widget_focusable(_mock_widget(visible=False))
    assert not is_widget_focusable(_mock_widget(enabled=False))
    assert not is_widget_focusable(_mock_widget(no_focus=True))
    assert is_widget_focusable(_mock_widget())
