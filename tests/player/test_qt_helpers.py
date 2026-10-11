from PyQt6.QtCore import Qt

from quiz_offline.ui.qt_helpers import is_checkbox_checked


def test_is_checkbox_checked_accepts_enum():
    assert is_checkbox_checked(Qt.CheckState.Checked) is True
    assert is_checkbox_checked(Qt.CheckState.Unchecked) is False
    assert is_checkbox_checked(Qt.CheckState.PartiallyChecked) is False


def test_is_checkbox_checked_accepts_int():
    assert is_checkbox_checked(Qt.CheckState.Checked.value) is True
    assert is_checkbox_checked(Qt.CheckState.Unchecked.value) is False
