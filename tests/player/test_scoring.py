from quiz_offline import scoring


def test_multiple_linear_only_corrects():
    assert scoring.multiple_linear_weight({1, 2}, {1, 2}, {3, 4}) == 1.0


def test_grade_from_weighted_percent_room_thresholds():
    thresholds = {
        "grade_3_min_percent": 70,
        "grade_4_min_percent": 80,
        "grade_5_min_percent": 90,
    }
    assert scoring.grade_from_weighted_percent(95, thresholds=thresholds) == 5
    assert scoring.grade_from_weighted_percent(85, thresholds=thresholds) == 4
    assert scoring.grade_from_weighted_percent(75, thresholds=thresholds) == 3
    assert scoring.grade_from_weighted_percent(50, thresholds=thresholds) == 2


def test_weighted_sum_to_percent():
    assert scoring.weighted_sum_to_percent(2.0, 4) == 50
