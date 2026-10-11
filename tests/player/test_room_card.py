from quiz_offline.ui.formatters import format_attempts_allowance


def test_format_attempts_allowance_limited():
    assert format_attempts_allowance(unlimited=False, allowed=3) == "3 попытки"
    assert format_attempts_allowance(unlimited=False, allowed=1) == "1 попытка"
    assert format_attempts_allowance(unlimited=False, allowed=5) == "5 попыток"


def test_format_attempts_allowance_unlimited():
    assert format_attempts_allowance(unlimited=True, allowed=None) == (
        "без ограничения попыток"
    )
