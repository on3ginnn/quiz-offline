# Quiz Offline — описание проекта

Windows-программа (PyQt6) для офлайн-прохождения тестов. Работает с пакетами комнат (JSON, `schema_version = 3`), выгруженными с сайта колледжа («Выгрузить офлайн» в меню комнаты). Выделена из репозитория `almetMedCollege` (`quiz-offline/`) в самостоятельный проект; код с сайтом не связан, общий только формат пакета.

## Стек
Python ≥ 3.12, PyQt6 ≥ 6.7, SQLite (журнал), pytest, PyInstaller (сборка exe).

## Структура
```
quiz_offline/
  main.py            точка входа (скрипт quiz-offline)
  config.py          portable-пути: data/ и rooms/ рядом с exe, fallback %LOCALAPPDATA%/AlmetQuizOffline
  models.py          модели пакета комнаты
  room_loader.py     парсинг и валидация JSON schema v3
  selection.py       выбор вопросов (в т.ч. квоты по темам)
  scoring.py, attempt_grading.py   оценка попытки
  storage.py         журнал участников (data/journal.sqlite)
  ui/                окна и виджеты (home, hall, taking, results, диалоги, тема)
tests/               pytest
quiz_offline.spec    конфиг PyInstaller
```

## Команды
```bash
python -m venv venv && venv\Scripts\activate
pip install -e ".[dev,build]"
python -m quiz_offline.main      # запуск
pytest                           # тесты
pyinstaller quiz_offline.spec    # сборка → dist/QuizOffline/QuizOffline.exe
```

## Данные и запуск с флешки
`data/journal.sqlite` и `rooms/` создаются рядом с exe; запускать нужно с носителя, чтобы журнал не разъезжался по компьютерам. `data/`, `rooms/`, `*.sqlite` в git не коммитить (персональные данные участников).

## Сценарий
Добавить комнату (JSON) → «Войти» → «Начать попытку» (ФИО) → прохождение (клавиатура ↑↓/Enter) → результат (оценка N из 5). Параметры (время, попытки, пороги, shuffle, квоты) берутся из пакета.

## Репозиторий
`git@github.com:on3ginnn/quiz-offline.git`, ветка `main`. История старого репозитория сайта не переносилась.
