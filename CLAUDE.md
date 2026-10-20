# Voice Assistant

Голосовой и текстовый ассистент для задач, напоминаний и встреч. Многопользовательский, вход через Яндекс ID, события синхронизируются с Яндекс Календарём.

## Стек

- **backend/** — FastAPI, SQLAlchemy 2.0 + Alembic, psycopg 3, PostgreSQL 18, httpx, caldav, GigaChat (REST)
- **frontend/** — React 18 + TypeScript + Vite, Tailwind v4 + shadcn/ui, react-router 7; запросы к API через прокси `/api`
- **compose.yaml** — `db`, `backend` (:8000), `frontend` (:5173); исходники монтируются томами, секреты — из `.env` в корне

## Запуск

```
cp .env.example .env   # заполнить ключи
docker compose up --build
```

- Фронт: http://localhost:5173, API: http://localhost:8000/docs
- Без Docker: бэкенд `cd backend && .venv/bin/uvicorn app.main:app --reload` (база по умолчанию — локальный Postgres `localhost:5432`, роль/БД `assistant`, пароль `localdev`), фронт `cd frontend && npm run dev`. Оба читают `.env` из корня.
- Миграции применяются при старте бэкенда (`alembic upgrade head`). Новая миграция: `alembic revision --autogenerate -m "..."` в `backend/`
- Тесты бэкенда (SQLite, внешние сервисы подменены): `pip install -r requirements-dev.txt && pytest` в `backend/`
- Фронт: `npm run build`, `npm run lint` (steiger, FSD)

## Docker и CI

- `compose.yaml` — разработка: сборка из исходников, hot reload (бэкенд `--reload` задан в compose, фронт — стадия `dev` Dockerfile).
- `compose.prod.yaml` — прод из готовых образов `ghcr.io/crepythecreator/voices-assistant-{backend,frontend}:${IMAGE_TAG:-latest}`; нужен `.env` с `POSTGRES_PASSWORD` (без спецсимволов — идёт в URL).
- `backend/Dockerfile` — прод-образ: не-root, миграции при старте, healthcheck `/health`, без `--reload`.
- `frontend/Dockerfile` — стадии `deps` → `dev` (Vite) / `build` → `prod` (nginx: статика + прокси `/api/` → `API_UPSTREAM`, `nginx.conf.template`). `VITE_*` вшиваются при сборке (build args).
- `.github/workflows/docker.yml` — тесты бэкенда, линтер и сборка фронта, затем образы linux/amd64+arm64 в GHCR: push в `main` → `latest` + `sha-xxxx`, тег `v1.2.3` → `1.2.3`, `1.2`; в PR — только сборка. `VITE_STT_ENGINE` для образа — переменная репозитория (Settings → Variables).

## Решения

- **Авторизация** — OAuth Яндекс ID (authorization code + PKCE + state в зашифрованной cookie). Сессия — httpOnly cookie, в БД только sha256. Токены Яндекса хранятся зашифрованными (Fernet от `APP_SECRET_KEY`), обновляются по refresh_token.
- **ИИ не меняет календарь сам.** GigaChat получает функции: `list_events` (чтение) и `propose_create/update/delete_event`. «Изменяющие» функции только валидируют аргументы и создают `ProposedAction(status=pending)`; ошибки валидации возвращаются модели. Календарь меняется только в `POST /actions/{id}/confirm` по нажатию пользователя — с повторной проверкой (не просрочено (24 ч), событие существует и принадлежит пользователю, не применено дважды). Это же защищает от prompt injection через названия событий.
- **Яндекс Календарь** — публичного REST API нет, работаем по CalDAV (`caldav.yandex.ru`, логин — email, пароль — OAuth-токен). Наши события пишем в отдельный календарь `YANDEX_CALENDAR_NAME` (MKCALENDAR; если не дали создать — в основной). Остальные календари только читаем — как занятость (`source=yandex`, `readonly`). Источник правды — наша БД; ошибка выгрузки помечает событие `sync_status=error`, повтор — `POST /calendar/sync`.
  - Нужное право OAuth — `calendar:all` (с `calendar:events.write` CalDAV отвечает 401).
  - Яндекс игнорирует адрес и имя из MKCALENDAR: календарь получает адрес `events-<id>` и имя OAuth-приложения («Voices»), переименование не применяется. Поэтому новый календарь ищем сравнением списков до/после и храним его URL в `calendar_links`. PUT по несуществующему адресу календаря даёт 409.
  - Время в iCal пишем в UTC (`as_utc` переводит aware-даты из psycopg в UTC), иначе уходит `TZID` без `VTIMEZONE`.
- **Даты в промпте** — модели плохо считают дни недели, поэтому в системный промпт подставляется таблица ближайших 14 дат с днями недели.
- **Время** хранится в UTC; модель работает в часовом поясе пользователя (приходит с фронта в `/chat`).

## Бэкенд (`backend/app/`)

```
main.py, config.py, db.py, models.py, security.py (шифрование, сессии, current_user), stt.py (SpeechKit)
auth/       yandex.py (OAuth-клиент, профиль, refresh), router.py (/auth/*)
calendar/   ical.py, yandex_caldav.py (CalDAV-клиент), service.py (синхронизация, занятость), router.py
assistant/  llm.py (интерфейс), gigachat.py (REST-клиент), tools.py (функции модели), actions.py (предложения,
            валидация, применение), agent.py (промпт и цикл), router.py (/chat, /actions)
```

Таблицы: `users`, `yandex_tokens`, `sessions`, `calendar_links`, `events`, `chat_messages`, `proposed_actions`.

API:
- `GET /auth/yandex/login?next=` → oauth.yandex.ru; `GET /auth/yandex/callback` → cookie + редирект на `FRONTEND_URL + next`, ошибка → `/login?error=<код>`; `GET /auth/me`; `POST /auth/logout`
- `POST /chat` `{message, source, timezone}` → `{reply, message: {id, role, text, createdAt, actions: [...]}}`; `GET /chat/history`
- `POST /actions/{id}/confirm`, `POST /actions/{id}/reject` → `{id, type, summary, status, error, eventId, expiresAt}`
- `GET /events?from&to` → наши события + занятость из Яндекса; `GET /calendar/status`; `POST /calendar/sync`
- `POST /stt?sample_rate=16000&lang=ru-RU`, тело — PCM s16le моно → `{text}`

## Фронтенд

Архитектура — **Feature-Sliced Design**. Слои (импорт только сверху вниз): `app → pages → widgets → features → entities → shared`.
- Слайсы импортируются только через публичный API (`index.ts`), между слайсами одного слоя импортов нет (между сущностями — через `@x`).
- Сегменты внутри слайса: `ui/`, `model/`, `api/`, `lib/`, `config/`.
- Проверка: `npm run lint` (steiger). Правило `fsd/insignificant-slice` выключено, пока страница одна.

```
src/
  app/        main.tsx, App.tsx (AuthProvider + RouterProvider), routes/ (router, guards), styles/
  pages/      assistant (шапка, чат, календарь), login (вход/регистрация через Яндекс ID)
  widgets/    header, chat (ChatPanel, Composer, MessageList), calendar-panel (+ model/useMonthEvents)
  features/   send-message (useChat, /chat, история), confirm-action (Подтвердить/Отклонить),
              voice-input (распознавание речи), auth (AuthProvider, UserMenu, YandexLoginButton), toggle-theme
  entities/   message, action (ProposedAction, ActionCard), event (getEvents, EventCard, invalidateEvents), user
  shared/     ui (shadcn), api (fetch-клиент, ApiError, обработчик 401), config (USE_MOCKS, STT_ENGINE, routes), lib
```

- Распознавание речи: `VITE_STT_ENGINE=browser` (Web Speech API; в Яндекс Браузере/Brave/Arc даёт `network`) или `server` (PCM 16 кГц → `POST /stt`).
- Роутинг: `/login` (`GuestRoute`), `/` (`ProtectedRoute`, гостя → `/login?next=…`). Любой 401 от API сбрасывает пользователя.
- После подтверждения действия `invalidateEvents()` перезагружает календарь.
- `VITE_USE_MOCKS=true` — работа без бэкенда (по умолчанию выключено; Vite читает `.env` из корня, `envDir`) (тестовый пользователь, фиктивные ответы и события).

## Референс

Старая версия лежит в `../Voice-assistant_Gorky_Kod/`. Использовать как источник идей, не как часть проекта. Не изменять.

## Открытые вопросы

- Доставка напоминаний (сейчас — только VALARM в Яндекс Календаре)
- Точные названия прав Календаря в OAuth-приложении не проверены на живом приложении — при пустом `YANDEX_OAUTH_SCOPE` запрашиваются все права приложения
- Двусторонняя синхронизация (правки в Яндексе пока не возвращаются к нам)
