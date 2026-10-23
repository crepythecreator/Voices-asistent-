# Voice Assistant

Голосовой и текстовый ассистент для задач, напоминаний и встреч. Вход по почте и паролю или через
Яндекс ID и Google, ИИ — GigaChat. В настройках можно подключить Яндекс и Google Календарь: события
ассистента попадут в отдельный календарь, а занятость будет учитываться. ИИ только предлагает
изменения — применяются они после подтверждения пользователем.

```
backend/    FastAPI + SQLAlchemy + Alembic + PostgreSQL
frontend/   React + TypeScript (Vite), Feature-Sliced Design
compose.yaml
```

## Настройка

1. `cp .env.example .env` и сгенерируйте `APP_SECRET_KEY`.
2. **Яндекс ID** (необязательно): создайте приложение на https://oauth.yandex.ru/client/new
   - платформа «Веб-сервисы», Redirect URI: `http://localhost:5173/api/auth/yandex/callback`;
   - права: «Доступ к логину, имени», «Доступ к адресу почты» и Календарь — полный доступ (`calendar:all`);
   - `ClientID` и `Client secret` → `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`.
3. **Google** (необязательно): в https://console.cloud.google.com
   - APIs & Services → Library → включите **Google Calendar API**;
   - OAuth consent screen → External, добавьте свой Google-аккаунт в **Test users**;
   - Credentials → Create credentials → OAuth client ID → Web application,
     Authorized redirect URI: `http://localhost:5173/api/auth/google/callback`;
   - Client ID и Client secret → `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

   Провайдер без ключей просто не показывается на странице входа — регистрация по почте работает всегда.
4. **GigaChat**: в https://developers.sber.ru/studio создайте проект GigaChat API и скопируйте «Ключ авторизации»
   в `GIGACHAT_CREDENTIALS`.
5. (Необязательно) **SpeechKit** для серверного распознавания речи: `VITE_STT_ENGINE=server`, `YANDEX_API_KEY`.

## Запуск

```
docker compose up --build
```

- Фронт: http://localhost:5173 (запросы к API идут через прокси `/api`)
- API: http://localhost:8000, документация: http://localhost:8000/docs

## Тесты

```
cd backend && pip install -r requirements-dev.txt && pytest
cd frontend && npm run build && npm run lint
```

## Образы и деплой

GitHub Actions (`.github/workflows/docker.yml`) на каждый push в `main` прогоняет тесты и публикует образы в GitHub Container Registry:

- `ghcr.io/crepythecreator/voices-assistant-backend`
- `ghcr.io/crepythecreator/voices-assistant-frontend` (nginx со статикой, проксирует `/api` на бэкенд)

Теги: `latest` и `sha-<коммит>`; для git-тега `v1.2.3` — ещё `1.2.3` и `1.2`.

Запуск на сервере (рядом нужен `.env`, см. `.env.example`, плюс `POSTGRES_PASSWORD`):

```
docker compose -f compose.prod.yaml pull
docker compose -f compose.prod.yaml up -d
```
