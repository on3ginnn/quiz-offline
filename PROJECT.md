# Quiz Offline — описание проекта

Репозиторий содержит **два независимых Windows-приложения** (PyQt6):

1. **Quiz Offline** (`quiz_offline`) — плеер для тех, кто проходит тест. Загружает пакеты (JSON `schema_version = 3`), ведёт журнал участников.
2. **Quiz Admin** (`quiz_admin`) — конструктор для администраторов: создание тестов, мультитесты, сценарии прохождения, выгрузка пакета для плеера. Функционал конструктора перенесён из АИС колледжа (репозиторий `almetMedCollege`, ветка `upgrade`; в `update` мультитестов и экспорта комнат нет).

Общего кода у приложений нет. Единственный контракт между ними — JSON-пакет schema v3.

## Терминология
- **Тест** (`Quiz`) — только вопросы и варианты ответов: обычный (`single`) или мультитест (`composite`) из тем. Правил прохождения не содержит.
- **Сценарий прохождения** (`Scenario`) — объект, привязанный к тесту: время, попытки, перемешивание, режим выборки, показ результатов, пороги оценок 3/4/5, режим учёта попыток, размер выборки, квоты по темам. У теста может быть несколько сценариев.
- **Пакет** — выгружаемый файл = тест + один сценарий. Плеер принимает только пакет, «голый» тест не принимает.
- В JSON ключи исторические: `kind: "room_package"`, блок `room` (= сценарий), в плеере сценарий называется «комната». В UI админки слово «комната» не используется.

## Стек
Python ≥ 3.12, PyQt6 ≥ 6.7, SQLite, pytest, PyInstaller.

## Структура
```
quiz_offline/        плеер
  main.py            точка входа (скрипт quiz-offline)
  config.py          portable-пути: data/ и rooms/ рядом с exe, fallback %LOCALAPPDATA%/AlmetQuizOffline
  models.py          модели пакета комнаты
  room_loader.py     парсинг и валидация JSON schema v3
  selection.py       выбор вопросов (в т.ч. квоты по темам)
  scoring.py, attempt_grading.py   оценка попытки
  storage.py         журнал участников (data/journal.sqlite)
  ui/                окна и виджеты (home, hall, taking, results, диалоги, тема)
quiz_admin/          конструктор
  main.py            точка входа (скрипт quiz-admin)
  config.py          portable-пути: data/admin.sqlite и exports/ рядом с exe, fallback %LOCALAPPDATA%/AlmetQuizAdmin
  models.py          Quiz, Topic, QuestionDraft/OptionDraft, Scenario (+ POLICY_FIELDS), QuizSummary
  storage.py         AdminStorage: SQLite (quizzes, topics, questions, options, scenarios, scenario_topic_quotas)
  validation.py      правила вопросов, сценария и готового пакета (зеркало требований плеера)
  package_export.py  build_package_dict: тест + сценарий -> dict schema v3 (+ проверка)
  importers.py       импорт JSON: schema 1 (тест / массив вопросов), 2 (мультитест), 3 (пакет -> тест + сценарий)
  services.py        сохранение вопросов, тема из теста, объединение, дублирование, импорт, выгрузка
  ui/                библиотека тестов, редактор (вопросы / темы / сценарии), диалог сценария и квот
tests/player/        тесты плеера
tests/admin/         тесты конструктора (round-trip пакета через quiz_offline.room_loader)
quiz_offline.spec, quiz_admin.spec   конфиги PyInstaller
```

## Команды
```bash
python -m venv venv && venv\Scripts\activate
pip install -e ".[dev,build]"
python -m quiz_offline.main      # плеер
python -m quiz_admin.main        # конструктор
pytest                           # все тесты
pytest tests/admin               # только конструктор
pyinstaller quiz_offline.spec    # dist/QuizOffline/QuizOffline.exe
pyinstaller quiz_admin.spec      # dist/QuizAdmin/QuizAdmin.exe
```

## Формат пакета (schema v3)
```
{ "schema_version": 3, "kind": "room_package", "exported_at": ISO-8601,
  "quiz": { "title", "kind": "single"|"composite",
            "questions": [Q]  |  "topics": [{"topic_order","title","questions":[Q]}] },
  "room": { name, public_id, time_limit_mode auto|manual, time_limit_minutes, attempts_unlimited,
            allowed_attempts, shuffle_questions, shuffle_options, selection_mode per_attempt|per_participant,
            show_results, show_answers, show_correct_answers, grade_3/4/5_min_percent,
            grade_attempt_mode best|last, questions_sample_size },
  "topic_quotas": [{"topic_order","topic_title","question_count"}] }     # [] для single
Q = {"text","question_type": single|multiple,"options":[{"text","is_correct"}]}
```
`room.public_id` — UUID сценария (в админке хранится в `scenarios.public_id`). id вопросов/вариантов в пакет не попадают — плеер генерирует свои.

## Правила конструктора
- Вопрос: непустой текст, ≥2 варианта (≤500 символов каждый), ≥1 правильный; `single` — ровно 1 правильный.
- Сценарий: попытки 1..10 или без ограничения; лимит `manual` ≥1 мин (`auto` = 1 мин на вопрос); пороги `0 ≤ «3» < «4» < «5» ≤ 100`; размер выборки ≤ числу вопросов (только у обычного теста).
- Мультитест: каждая тема непустая; квота темы ≤ числа её вопросов; 0 — тема пропускается; без квоты — тема целиком.
- Пакет не выгружается, пока не пройдёт проверку `validate_package_dict`.

## Данные и запуск с флешки
Плеер: `data/journal.sqlite` и `rooms/` рядом с exe — запускать с носителя, чтобы журнал не разъезжался по компьютерам.
Конструктор: `data/admin.sqlite` (библиотека тестов) и `exports/` рядом с exe. `data/`, `rooms/`, `exports/`, `*.sqlite` в git не коммитить (персональные данные участников и содержимое тестов).

## Сценарий работы
Админ: «Новый тест» (или импорт JSON) → вопросы → при необходимости «Объединить в мультитест» / темы → вкладка «Сценарии прохождения» → настройки и квоты → «Выгрузить пакет для плеера».
Участник: плеер → «+ Добавить комнату» (JSON пакета) → «Войти» → «Начать попытку» (ФИО) → прохождение (↑↓/Enter) → результат (оценка N из 5). Параметры берутся из пакета.

## Вне объёма (пока не сделано)
Импорт вопросов из docx/xlsx/csv (в АИС был только JSON), предпросмотр/пробное прохождение в админке, просмотр журналов результатов из плеера, переименование «комната» → «сценарий» в UI плеера.

## Репозиторий
`git@github.com:on3ginnn/quiz-offline.git`, ветка `main`. История старого репозитория сайта не переносилась.
