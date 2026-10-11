# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Rules & Instructions

## Core Directives

- Перед тем как что-то сделать или изменить код, обязательно изучи и прочитай файл @PROJECT.md.
- После того как внес любые изменения в код, ВСЕГДА актуализируй файл с описанием проекта и правил.

## Commands

Python 3.12+, Windows, PyQt6. Venv лежит в `venv/` (в git не входит). Подробности — в `PROJECT.md`.

```bash
pip install -e ".[dev]"            # dev-установка (pytest)
python -m quiz_offline.main        # плеер (или команда quiz-offline)
python -m quiz_admin.main          # конструктор (или команда quiz-admin)
pytest                             # все тесты (tests/player + tests/admin)
pytest tests/player/test_scoring.py::test_name   # один тест
pip install -e ".[build]" && pyinstaller quiz_offline.spec   # dist/QuizOffline/QuizOffline.exe
pyinstaller quiz_admin.spec                                  # dist/QuizAdmin/QuizAdmin.exe
```

Линтера/форматтера не настроено. Qt-тесты работают с `QT_QPA_PLATFORM=offscreen`; модальные диалоги (`show_errors` и т.п.) в тестах нужно подменять через monkeypatch, иначе тест зависнет. При ошибке `source code string cannot contain null bytes` при импорте PyQt6 — переустановить `PyQt6 PyQt6-Qt6 PyQt6-sip` с `--force-reinstall --no-cache-dir`.

## Architecture

В репозитории **два независимых приложения** без общего кода; контракт между ними — JSON-пакет `schema_version = 3`. Весь UI и тексты — на русском.

Терминология: **тест** (`Quiz`) — только вопросы; **сценарий прохождения** (`Scenario`) — как воспроизводить тест (время, попытки, пороги, квоты тем); **пакет** — тест + один сценарий, именно его читает плеер. В JSON сценарий называется `room` (`kind: "room_package"`), в UI плеера — «комната», в админке слово «комната» не используется.

### Плеер `quiz_offline/`
Слои без Qt и `ui/`:
- **Данные/логика:** `models.py` (`RoomPackage`, `RoomPolicy`, `Question`, `AttemptLayoutItem`, `AttemptResult`), `room_loader.py` (парсинг и валидация пакета, `RoomPackageError`), `selection.py` (порт серверного `select_attempt_questions`: простые и `composite`-тесты с квотами по темам, `per_participant` мутирует сохранённые выборки), `scoring.py` (копия `backend/quiz/scoring.py` АИС — держать синхронным), `attempt_grading.py` (взвешенный балл, оценка 3–5 по порогам пакета).
- **`storage.py`:** `Storage` над SQLite — реестр комнат, участники (`normalize_full_name`), попытки, выборки. Копирует JSON в `rooms/` и перечитывает при открытии.
- **`config.py`:** portable-пути; `data/` и `rooms/` рядом с exe (PyInstaller `sys.frozen`) или в корне репозитория; fallback — `%LOCALAPPDATA%/AlmetQuizOffline`.
- **`ui/`:** `main_window.py` — стек Home → Hall → Taking → Results (`_go_home/_open_hall/_start_attempt/_show_results/_retry_attempt`, контекст попытки — словарь); остальное — виджеты и хелперы (`theme.py`, `taking_keyboard.py`, `donut_chart.py`…).

Все параметры прохождения приходят из пакета, а не из настроек приложения.

### Конструктор `quiz_admin/`
- `storage.py` — `AdminStorage` (SQLite `data/admin.sqlite`): quizzes → topics (только composite) → questions → options; scenarios (все поля политики + `public_id` UUID) и `scenario_topic_quotas`. Банк вопросов — у теста (single) или у темы (composite); `replace_questions` — bulk-замена банка.
- `validation.py` — правила вопросов/сценария и `validate_package_dict` (зеркало требований `quiz_offline.room_loader`; при изменении формата править оба приложения). `package_export.build_package_dict` собирает и проверяет пакет, `PackageValidationError.errors` — список причин для UI.
- `services.py` — сохранение с валидацией, тема из теста (клон вопросов), `merge_quizzes`, дублирование, `import_quiz`, `build_package`/`export_package`. `importers.py` — JSON schema 1/2/3 (v3 создаёт тест и сценарий).
- `ui/` — `LibraryWidget` → `QuizEditorWidget` (вкладка «Вопросы» или «Темы и вопросы» + «Сценарии прохождения»); `QuestionsPanel` хранит черновики в памяти и сохраняет целиком, `confirm_leave()` спрашивает про несохранённое.
- Тесты `tests/admin/test_core.py` проверяют round-trip: пакет админки → `quiz_offline.room_loader.parse_room_package_dict` (единственное место, где пакеты видят друг друга).

Источник функционала конструктора — ветка `upgrade` репозитория almetMedCollege (`backend/quiz/{room_export,services,serializer,scoring}.py`); в ветке `update` мультитестов нет.
