from quiz_offline.ui.start_dialog import compose_full_name


def test_compose_full_name_with_middle():
    assert compose_full_name("Иванов", "Иван", "Иванович") == "Иванов Иван Иванович"


def test_compose_full_name_without_middle():
    assert compose_full_name("Петров", "Пётр", "") == "Петров Пётр"


def test_compose_full_name_strips_parts():
    assert compose_full_name("  Сидоров ", " Анна ", "  ") == "Сидоров Анна"
