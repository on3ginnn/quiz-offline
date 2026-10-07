"""Тесты подписи результата на 5-балльной шкале."""

from quiz_offline.ui.result_visual import format_grade_scale_caption


def test_format_grade_scale_caption():
    assert format_grade_scale_caption(2) == "2 из 5"
    assert format_grade_scale_caption(5) == "5 из 5"
