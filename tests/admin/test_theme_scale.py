"""Масштаб текста конструктора: допустимые значения и пересчёт размеров в QSS."""

from quiz_admin.ui.theme import SCALES, app_stylesheet, clamp_scale, next_scale


def test_clamp_scale_snaps_to_allowed_values():
    assert clamp_scale(1.1) == 1.0
    assert clamp_scale(1.4) == 1.5
    assert clamp_scale(99) == SCALES[-1]
    assert clamp_scale(0) == SCALES[0]


def test_next_scale_steps_and_stops_at_edges():
    assert next_scale(1.0, 1) == 1.25
    assert next_scale(2.0, 1) == 2.0
    assert next_scale(1.0, -1) == 1.0
    assert next_scale(1.5, -1) == 1.25


def test_stylesheet_scales_font_sizes():
    assert "font-size: 16px;" in app_stylesheet(1.0)
    assert "font-size: 32px;" in app_stylesheet(2.0)
    assert "font-size: 24px;" in app_stylesheet(1.5)
