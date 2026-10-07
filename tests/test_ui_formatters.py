from quiz_offline.ui.formatters import format_datetime_ru
from quiz_offline.ui.result_visual import outcome_for_percent


def test_format_datetime_ru():
    assert format_datetime_ru("2026-06-21T12:05:32+00:00").startswith("21.06.2026")
    assert format_datetime_ru(None) == "—"


def test_outcome_for_percent():
    fail = outcome_for_percent(6)
    assert fail.tone == "fail"
    warn = outcome_for_percent(55)
    assert warn.tone == "warn"
    ok = outcome_for_percent(85)
    assert ok.tone == "ok"
