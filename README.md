<div align="center">

# 🎙️ Voice Assistant

**Голосовой и текстовый ассистент для задач, напоминаний и встреч**

Говорите — ассистент предложит действие, вы подтвердите, и оно попадёт в календарь.

![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)

</div>

---

## Содержание

- [Возможности](#возможности)
- [Как это работает](#как-это-работает)
- [Технологии](#технологии)
- [Быстрый старт](#быстрый-старт)
- [Настройка интеграций](#настройка-интеграций)
- [Деплой на сервер](#деплой-на-сервер)
- [Разработка](#разработка)
- [Структура проекта](#структура-проекта)
- [Ограничения](#ограничения)

## Возможности

| | |
|---|---|
| 🗣️ **Режим беседы** | Нажали на сферу, сказали фразу — ассистент ответил голосом. Основной режим |
| 💬 **Чат** | Та же история и те же возможности в текстовом виде, переключатель «Голос / Чат» |
| 📅 **Календарь** | Виды «Месяц» и «Список» (доска событий по датам), фильтр по типам |
| 🔄 **Синхронизация** | Отдельный календарь в Яндекс Календаре и Google Calendar, учёт занятости из остальных календарей |
| ✅ **Подтверждение** | Режимы «С подтверждением» и «Авто» (удаление всегда подтверждается) |
| 🔐 **Вход** | Почта и пароль, Яндекс ID, Google; аккаунты связываются по почте |
| 👥 **Мультипользовательность** | У каждого свои события, подключённые календари и настройки |

## Как это работает

```
 голос ──► распознавание ──► GigaChat ──► предложение действия ──► подтверждение ──► БД ──► Яндекс / Google
           (браузер или      (понимает      (создать / изменить /     (кнопка или      │
            сервер GigaASR)   намерение)     удалить событие)          голос «да»)     └─► календарь на экране
```

- **ИИ ничего не меняет сам.** GigaChat может читать календарь и *предлагать* изменения. Применяет их только
  сервер после подтверждения пользователя. В режиме «Авто» создание и изменение применяются сразу,
  удаление — всё равно по подтверждению.
- **Источник правды — наша база.** События выгружаются в календари провайдеров, правки оттуда пока не возвращаются.
- **Распознавание речи выбирается автоматически.** В Chrome и Safari — встроенное в браузер; в Яндекс Браузере оно
  недоступно сайтам, поэтому звук уходит на сервер (Cloud.ru GigaASR). Ответы озвучивает Cloud.ru SaluteSpeech,
  без ключа — голос браузера.

## Технологии

| Слой | Стек |
|---|---|
| Фронтенд | React 18, TypeScript, Vite, Tailwind v4, shadcn/ui, react-router 7, архитектура Feature-Sliced Design |
| Бэкенд | FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 18, httpx |
| ИИ и речь | GigaChat, Cloud.ru (GigaASR, SaluteSpeech), запасной Yandex SpeechKit |
| Календари | Яндекс Календарь по CalDAV, Google Calendar REST API v3 |
| Инфраструктура | Docker Compose, nginx, GitHub Actions → GitHub Container Registry |

## Быстрый старт

Нужны Docker и ключ GigaChat (остальное необязательно).

```bash
cp .env.example .env     # затем заполните ключи, см. ниже
docker compose up --build
```

| Что | Адрес |
|---|---|
| Приложение | http://localhost:5173 |
| API и документация | http://localhost:8000/docs |

Миграции базы применяются при старте. Регистрация по почте работает сразу, кнопки Яндекса и Google
активируются, когда заданы их ключи.

<details>
<summary><b>Запуск без Docker</b></summary>

1. Локальный PostgreSQL на `localhost:5432`, роль и база `assistant`, пароль `localdev`.
2. Бэкенд: `cd backend && .venv/bin/uvicorn app.main:app --reload`
3. Фронт: `cd frontend && npm run dev`

Оба читают `.env` из корня проекта.
</details>

## Настройка интеграций

Все ключи — в `.env` (шаблон: `.env.example`).

| Переменная | Где взять | Обязательно |
|---|---|---|
| `APP_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` | да |
| `GIGACHAT_CREDENTIALS` | [developers.sber.ru/studio](https://developers.sber.ru/studio) → проект GigaChat API → «Ключ авторизации» | да, для ИИ |
| `CLOUDRU_API_KEY` | [console.cloud.ru](https://console.cloud.ru) → Foundation Models → API-ключи | нет: синтез речи и распознавание в Яндекс Браузере |
| `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET` | [oauth.yandex.ru](https://oauth.yandex.ru/client/new) | нет: вход и календарь Яндекса |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | [console.cloud.google.com](https://console.cloud.google.com) | нет: вход и календарь Google |

<details>
<summary><b>Яндекс ID</b></summary>

- Платформа «Веб-сервисы», Redirect URI: `http://localhost:5173/api/auth/yandex/callback`
- Права: «Доступ к логину, имени», «Доступ к адресу почты» и Календарь — полный доступ (`calendar:all`)
</details>

<details>
<summary><b>Google</b></summary>

1. APIs & Services → Library → включите **Google Calendar API**.
2. OAuth consent screen → External, добавьте свой аккаунт в **Test users**.
3. Credentials → Create credentials → OAuth client ID → Web application,
   Authorized redirect URI: `http://localhost:5173/api/auth/google/callback`.
</details>

На проде Redirect URI меняются на адрес сайта: `https://<домен>/api/auth/{yandex|google}/callback`.

## Деплой на сервер

Образы собирает GitHub Actions (`.github/workflows/docker.yml`): тесты бэкенда, линтер и сборка фронта, затем публикация
в GitHub Container Registry.

| Образ | Теги |
|---|---|
| `ghcr.io/crepythecreator/voices-assistant-backend` | `latest` и `sha-<коммит>` для push в `main`; `1.2.3`, `1.2` для git-тега `v1.2.3` |
| `ghcr.io/crepythecreator/voices-assistant-frontend` | то же; nginx со статикой, проксирует `/api` на бэкенд |

### 1. Подготовка

```bash
cp .env.prod.example .env    # заполните: DOMAIN, POSTGRES_PASSWORD, APP_SECRET_KEY, FRONTEND_URL, redirect URI, ключи
```

`POSTGRES_PASSWORD` — без спецсимволов (`@ : / # ? %`): он подставляется в URL подключения.
`openssl rand -hex 24` подойдёт.

### 2. Сертификат Let's Encrypt

nginx в контейнере читает сертификат из `/etc/letsencrypt/live/<DOMAIN>/` хоста. DNS домена должен указывать на сервер,
порты 80 и 443 — быть открыты.

**Первый выпуск.** Порт 80 свободен (стек ещё не запущен):

```bash
sudo certbot certonly --standalone -d example.com
```

**Продление без остановки сайта** (после запуска из шага 3). nginx уже отдаёт `/.well-known/acme-challenge/` из `/var/www/certbot`, поэтому
переключите certbot на webroot и перезагружайте nginx после продления:

```bash
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d example.com --force-renewal   # один раз, чтобы сохранить метод
```

Файл `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh`:

```bash
#!/bin/sh
docker compose -f /путь/к/проекту/compose.prod.yaml exec -T frontend nginx -s reload
```

```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

Автоматическое продление обычно уже включено (`systemctl list-timers | grep certbot`); проверка: `sudo certbot renew --dry-run`.

### 3. Запуск

```bash
docker compose -f compose.prod.yaml pull
docker compose -f compose.prod.yaml up -d
```

- Порт 80 перенаправляет на HTTPS (`301`), порт 443 отдаёт сайт; бэкенд получает `X-Forwarded-Proto: https`.
- Обновление: `pull` и `up -d` ещё раз. База хранится в томе `postgres_data`.
- Нужная версия: `IMAGE_TAG=1.2.3` в `.env`.
- Если контейнер фронтенда не стартует, проверьте, что `/etc/letsencrypt/live/<DOMAIN>/fullchain.pem` существует и
  `DOMAIN` в `.env` совпадает с доменом сертификата.

> `APP_SECRET_KEY` не меняйте после запуска: сохранённые токены Яндекса и Google перестанут расшифровываться.

## Разработка

```bash
cd backend && pip install -r requirements-dev.txt && pytest     # тесты бэкенда (SQLite, внешние сервисы подменены)
cd frontend && npm run build && npm run lint                    # сборка и проверка архитектуры FSD (steiger)
```

- Новая миграция: `alembic revision --autogenerate -m "..."` в `backend/`.
- `VITE_USE_MOCKS=true` — фронт работает без бэкенда, на моках.
- `VITE_STT_ENGINE=auto | browser | server` — движок распознавания речи.

Подробные решения и архитектура — в [CLAUDE.md](CLAUDE.md).

## Структура проекта

```
backend/
  app/
    auth/        вход по паролю и OAuth Яндекс/Google, сессии
    account/     подключения, синхронизация, пароль
    calendar/    CalDAV Яндекса, Google Calendar, выгрузка и занятость
    assistant/   GigaChat, функции модели, предложения и подтверждение действий
    stt.py       серверное распознавание речи
    tts.py       синтез речи
  migrations/    Alembic
  tests/
frontend/
  src/           app → pages → widgets → features → entities → shared (Feature-Sliced Design)
  nginx.conf.template   конфиг прод-образа: HTTPS, редирект с 80, прокси /api
compose.yaml        разработка (hot reload)
compose.prod.yaml   прод из готовых образов
```

## Ограничения

- Напоминания доставляются только средствами Яндекс Календаря (`VALARM`), своей доставки нет.
- Нет подтверждения почты и сброса пароля письмом — проект не отправляет писем.
- Синхронизация односторонняя: правки в Яндексе и Google к нам не возвращаются.
- Google OAuth в режиме Testing пускает только добавленных тестовых пользователей; для публичного запуска приложение
  нужно верифицировать.
