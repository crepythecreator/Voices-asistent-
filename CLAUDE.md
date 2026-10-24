# Voice Assistant

Голосовой и текстовый ассистент для задач, напоминаний и встреч. Многопользовательский: вход по почте и паролю или через Яндекс ID / Google; события синхронизируются с Яндекс и Google Календарём.

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

- **Авторизация** — почта+пароль (argon2, без подтверждения почты и сброса пароля — писем нет; лимит 10 неудачных входов за 15 мин на почту и на IP) и OAuth Яндекс/Google (authorization code + PKCE + state в зашифрованной cookie, один callback `/auth/{provider}/callback` для входа и подключения). Сессия — httpOnly cookie, в БД только sha256. Токены провайдеров хранятся зашифрованными (Fernet от `APP_SECRET_KEY`), обновляются по refresh_token; если ключ сменили — токен считается недоступным.
  - **Вход** через провайдера просит только профиль (Яндекс `login:info login:email`, Google `openid email profile`) и не трогает токены уже подключённого аккаунта (иначе потеряли бы доступ к календарю). **Подключение** из настроек (`/auth/{provider}/connect`) просит календарь: Яндекс `calendar:all`; Google `calendar.app.created` (свой календарь) + `calendar.calendarlist.readonly` + `calendar.events.readonly` (занятость), `access_type=offline`, `prompt=consent`.
  - **Связка по почте**: вход через провайдера с подтверждённой почтой попадает в аккаунт с этой почтой; если почта аккаунта не была подтверждена (регистрация по паролю), пароль сбрасывается и сессии завершаются — защита от захвата чужой почты. Неподтверждённая почта провайдера не связывается. На пользователя — не больше одного аккаунта каждого провайдера; отключить последний способ входа нельзя.
- **ИИ не применяет изменения сам.** GigaChat получает функции: `list_events` (чтение) и `propose_create/update/delete_event`. «Изменяющие» функции валидируют аргументы и создают `ProposedAction`; ошибки валидации возвращаются модели. Применяет действие только `apply_action` — с повторной проверкой (не просрочено (24 ч), событие существует и принадлежит пользователю, не применено дважды). Кто его вызывает — режим пользователя `users.confirm_mode` (настройки или переключатель на экране ассистента, `PATCH /account/settings`):
  - `confirm` (по умолчанию) — только пользователь: кнопкой или голосом (`POST /actions/{id}/confirm`);
  - `auto` — создание и изменение применяет сервер сразу внутри `tools.execute` (модель получает `status=applied` и промпт про авто-режим), **удаление всё равно ждёт подтверждения** (`AUTO_APPLY_TYPES`) — оно необратимо, а текст из чужих календарей мог бы подтолкнуть модель удалить лишнее.
- **Календари** — события ассистента (источник правды — наша БД) выгружаются в отдельный календарь каждого подключённого аккаунта с доступом к календарю и включённым `sync_enabled` (переключатель в настройках); статус по каждому — `event_syncs`, повтор — `POST /calendar/sync`. Занятость читается из остальных календарей всех аккаунтов с доступом (`source=yandex|google`, `readonly`). Отключение аккаунта не удаляет уже выгруженные события у провайдера.
- **Яндекс Календарь** — публичного REST API нет, работаем по CalDAV (`caldav.yandex.ru`, логин — email, пароль — OAuth-токен).
- **Google Calendar** — REST API v3 (`calendar/google_calendar.py`): календарь `CALENDAR_NAME` создаётся через `POST /calendars`, события — с `extendedProperties.private.voicesEventId`.
  - Нужное право OAuth — `calendar:all` (с `calendar:events.write` CalDAV отвечает 401).
  - Яндекс игнорирует адрес и имя из MKCALENDAR: календарь получает адрес `events-<id>` и имя OAuth-приложения («Voices»), переименование не применяется. Поэтому новый календарь ищем сравнением списков до/после и храним его URL в `oauth_accounts.calendar_id`. PUT по несуществующему адресу календаря даёт 409.
  - Время в iCal пишем в UTC (`as_utc` переводит aware-даты из psycopg в UTC), иначе уходит `TZID` без `VTIMEZONE`.
- **Даты в промпте** — модели плохо считают дни недели, поэтому в системный промпт подставляется таблица ближайших 14 дат с днями недели.
- **Время** хранится в UTC; модель работает в часовом поясе пользователя (приходит с фронта в `/chat`).

## Бэкенд (`backend/app/`)

```
main.py, config.py, db.py, models.py, security.py (шифрование, сессии, current_user), stt.py (серверное распознавание: Cloud.ru GigaASR/Whisper, запасной SpeechKit),
tts.py (синтез речи: GigaChat/SaluteSpeech через Realtime API Cloud.ru, WebSocket → WAV 24 кГц)
auth/       providers.py (Яндекс/Google OAuth), accounts.py (вход/связка/подключение, токены), passwords.py, router.py (/auth/*)
account/    router.py (/account/*: подключения, синхронизация, пароль)
calendar/   backend.py (интерфейс), yandex_caldav.py, google_calendar.py, ical.py, service.py (выгрузка во все включённые календари, занятость), router.py
assistant/  llm.py (интерфейс), gigachat.py (REST-клиент), tools.py (функции модели), actions.py (предложения,
            валидация, применение), agent.py (промпт и цикл), router.py (/chat, /actions)
```

Таблицы: `users` (email, password_hash, email_verified), `oauth_accounts` (провайдер, токены, доступ к календарю, sync_enabled, calendar_id), `sessions`, `events`, `event_syncs` (копия события у провайдера), `chat_messages`, `proposed_actions`. Миграция 0003 — `users.confirm_mode`. Миграция 0002 перенесла старые `yandex_tokens`/`calendar_links`; её откат не поддерживается.

API:
- `POST /auth/register` `{email, password, name}`, `POST /auth/login` `{email, password}`, `GET /auth/me` → `{id, name, email, avatarUrl, hasPassword}`, `POST /auth/logout`, `GET /auth/providers` → все провайдеры с `configured` (ненастроенный показывается неактивной кнопкой)
- `GET /auth/{yandex|google}/login?next=` и `/connect?next=` → провайдер; `GET /auth/{provider}/callback` → cookie + редирект на `FRONTEND_URL + next`; ошибка → `/login?error=` (вход) или `/settings?error=` (подключение): `access_denied`, `invalid_state`, `already_linked`, `other_account_connected`, `provider_error`; успех подключения → `/settings?connected=<provider>`
- `GET /account/connections`, `PATCH /account/connections/{provider}` `{syncEnabled}`, `DELETE /account/connections/{provider}`, `POST /account/password` `{currentPassword?, newPassword}` (завершает остальные сессии)
- `POST /chat` `{message, source, timezone}` → `{reply, message: {id, role, text, createdAt, actions: [...]}}`; `GET /chat/history`
- `PATCH /account/settings` `{confirmMode: confirm|auto}` → пользователь
- `POST /actions/{id}/confirm`, `POST /actions/{id}/reject` → `{id, type, summary, status, error, eventId, expiresAt}`
- `GET /events?from&to` → наши события (`syncStatus`: synced/pending/error) + занятость из Яндекса и Google; `POST /calendar/sync`
- `GET /stt/status`; `POST /stt?sample_rate=16000&lang=ru-RU`, тело — PCM s16le моно → `{text}`
- `POST /tts` `{text}` (≤1000 символов, разметка вырезается) → `audio/wav`; 503 без `CLOUDRU_API_KEY`

## Фронтенд

Архитектура — **Feature-Sliced Design**. Слои (импорт только сверху вниз): `app → pages → widgets → features → entities → shared`.
- Слайсы импортируются только через публичный API (`index.ts`), между слайсами одного слоя импортов нет (между сущностями — через `@x`).
- Сегменты внутри слайса: `ui/`, `model/`, `api/`, `lib/`, `config/`.
- Проверка: `npm run lint` (steiger). Правило `fsd/insignificant-slice` выключено, пока страница одна.

```
src/
  app/        main.tsx, App.tsx (AuthProvider + RouterProvider), routes/ (router, guards), styles/
  pages/      assistant (шапка, ассистент, календарь), login, register, settings (профиль, аккаунты и календари, пароль)
  widgets/    header, auth-layout (раскладка входа/регистрации), assistant-panel (AssistantPanel: режимы «Голос»/«Чат»,
              VoiceView, ChatView, Composer, MessageList), calendar-panel (виды «Месяц»/«Список», фильтр по типам) (+ model/useMonthEvents)
  features/   send-message (useChat, /chat, история), confirm-action (Подтвердить/Отклонить),
              voice-input (распознавание речи), voice-conversation (режим беседы: listenOnce, Speaker, да/нет/стоп), auth (AuthProvider, LoginForm, RegisterForm, OAuthButtons, UserMenu),
              manage-connections (карточки Яндекс/Google в настройках), change-password, confirm-mode (ConfirmModeSetting, ConfirmModeToggle), toggle-theme
  entities/   connection, message, action (ProposedAction, ActionCard), event (getEvents, EventCard, invalidateEvents, категории и цвета, groupByDay), user
  shared/     ui (shadcn + input, label, switch, form-error, provider-icon), api (fetch-клиент, ApiError, обработчик 401), config (USE_MOCKS, STT_ENGINE, routes, MIN_PASSWORD_LENGTH), lib (cn, errorMessage, форматирование)
```

- Распознавание речи: `VITE_STT_ENGINE=auto` (по умолчанию) | `browser` | `server`. В Яндекс Браузере Web Speech даёт `network` (облачный сервис недоступен сайтам, локальный пакет не скачивается, нативного API нет), поэтому `shared/lib/speechEngine.ts` выбирает сервер: Яндекс Браузер, нет Web Speech или флаг `stt-browser-broken` (ставится при `network`, 24 ч). Серверный путь — запись PCM 16 кГц (`shared/lib/recorder.ts`) → `POST /stt`; в беседе конец фразы определяет энергетический VAD (`listenOnceServer`), `listen()` переключается на сервер при `network`. Бэкенд: `STT_PROVIDER=auto` (Cloud.ru при `CLOUDRU_API_KEY`, иначе Яндекс SpeechKit), `STT_MODEL=GigaChat/GigaASR`, запасная `openai/whisper-large-v3`; `GET /stt/status` → `{available, provider}`. Проверено на бэкенде и образце речи; сквозной прогон в браузере с подменой микрофона не удался, на живом микрофоне VAD не проверялся.
- Роутинг: `/login`, `/register` (`GuestRoute`), `/`, `/settings` (`ProtectedRoute`, гостя → `/login?next=…`). Любой 401 от API сбрасывает пользователя.
- После подтверждения действия `invalidateEvents()` перезагружает календарь.
- **Календарь** (`widgets/calendar-panel`): «Месяц» — сетка с цветными точками по типам (свой `DayButton` через контекст) и события выбранного дня; «Список» — доска предстоящих событий по датам с липкими заголовками, догрузка окнами по 30 дней. Фильтр по типам (встречи / напоминания / задачи / другие календари) — он же легенда цветов. Вид и фильтр запоминаются в localStorage; данные грузятся только для активного вида. Внешние события на весь день приходят с `allDay`.
- **Голос — основной режим** (`widgets/assistant-panel`): большая кнопка-сфера `VoiceOrb`, статус, последняя реплика и карточки подтверждения. Переключатель «Голос / Чат» запоминается в localStorage (`assistant-mode`); оба режима работают с одной историей и одной беседой (`model/useAssistant.ts`), начатая беседа в чате продолжается компактной панелью.
- **Беседа** (оркестрация — `widgets/assistant-panel/model/useVoiceChat.ts`): слушаем фразу браузерным Web Speech (`continuous=false` — браузер сам ловит конец фразы) → `/chat` → озвучка по предложениям (`Speaker`: первый фрагмент короткий, следующий синтезируется, пока играет текущий; без `CLOUDRU_API_KEY` или при ошибке — `speechSynthesis` браузера). Пока ассистент говорит, микрофон не слушает (иначе услышит себя) — перебить кнопкой. «Стоп»/«хватит» и 3 паузы подряд завершают беседу.
  - Предложенные действия зачитываются с вопросом «Подтвердить?». Короткое «да»/«нет» обрабатывает не ИИ, а правило (`isYes`/`isNo` — только однозначные короткие фразы) и только для действий последнего ответа, через тот же `/actions/{id}/confirm|reject`.
- `VITE_USE_MOCKS=true` — работа без бэкенда (по умолчанию выключено; Vite читает `.env` из корня, `envDir`) (тестовый пользователь, фиктивные ответы и события).

## Референс

Старая версия лежит в `../Voice-assistant_Gorky_Kod/`. Использовать как источник идей, не как часть проекта. Не изменять.

## Открытые вопросы

- Доставка напоминаний (сейчас — только VALARM в Яндекс Календаре)
- Подтверждение почты и сброс пароля письмом (нужен SMTP)
- Google OAuth в режиме Testing: войти могут только Test users; для публичного запуска нужна верификация приложения (calendar.* — чувствительные права)
- Двусторонняя синхронизация (правки в Яндексе пока не возвращаются к нам)
