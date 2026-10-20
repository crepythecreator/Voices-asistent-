# Voice Assistant

Голосовой и текстовый ассистент для задач, напоминаний и встреч. Вход через Яндекс ID, ИИ — GigaChat,
события синхронизируются с отдельным календарём в Яндекс Календаре. ИИ только предлагает изменения —
применяются они после подтверждения пользователем.

```
backend/    FastAPI + SQLAlchemy + Alembic + PostgreSQL
frontend/   React + TypeScript (Vite), Feature-Sliced Design
compose.yaml
```

## Настройка

1. `cp .env.example .env` и сгенерируйте `APP_SECRET_KEY`.
2. **Яндекс ID**: создайте приложение на https://oauth.yandex.ru/client/new
   - платформа «Веб-сервисы», Redirect URI: `http://localhost:5173/api/auth/yandex/callback`;
   - права: доступ к логину, имени, почте и аватару, а также к Календарю (CalDAV);
   - `ClientID` и `Client secret` → `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`.
3. **GigaChat**: в https://developers.sber.ru/studio создайте проект GigaChat API и скопируйте «Ключ авторизации»
   в `GIGACHAT_CREDENTIALS`.
4. (Необязательно) **SpeechKit** для серверного распознавания речи: `VITE_STT_ENGINE=server`, `YANDEX_API_KEY`.

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
