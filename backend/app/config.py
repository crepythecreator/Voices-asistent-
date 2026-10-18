from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env лежит в корне репозитория (его же читает docker compose)
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
# backend/certs локально и /srv/certs в контейнере
CERTS_DIR = Path(__file__).resolve().parents[1] / "certs"


class Settings(BaseSettings):
    # Переменные окружения важнее файла: в Docker compose передаёт их сам
    model_config = SettingsConfigDict(env_file=ROOT_ENV, extra="ignore")

    database_url: str = "postgresql+psycopg://assistant:localdev@localhost:5432/assistant"
    app_timezone: str = "Europe/Moscow"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Ключ для шифрования токенов Яндекса и служебных cookie. В проде — обязательно свой.
    app_secret_key: str = "dev-secret-change-me"
    # Куда возвращать пользователя после OAuth (фронт)
    frontend_url: str = "http://localhost:5173"
    # true на HTTPS — cookie будут с флагом Secure
    cookie_secure: bool = False
    session_ttl_days: int = 30

    # --- Яндекс ID (OAuth) — https://oauth.yandex.ru ---
    yandex_client_id: str | None = None
    yandex_client_secret: str | None = None
    # Должен в точности совпадать с Redirect URI в настройках приложения
    yandex_redirect_uri: str = "http://localhost:5173/api/auth/yandex/callback"
    # Пусто — токен получит все права, отмеченные в настройках приложения
    yandex_oauth_scope: str = ""

    # --- Яндекс Календарь (CalDAV) ---
    caldav_url: str = "https://caldav.yandex.ru/"
    yandex_calendar_name: str = "Голосовой ассистент"

    # --- Yandex Cloud: SpeechKit ---
    # API-ключ сервисного аккаунта с ролью ai.speechkit-stt.user
    yandex_api_key: str | None = None
    # Нужен только при авторизации IAM-токеном, для API-ключа можно не задавать
    yandex_folder_id: str | None = None

    # --- GigaChat ---
    # Ключ авторизации из личного кабинета (base64 от client_id:client_secret)
    gigachat_credentials: str | None = None
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2-Pro"
    gigachat_auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_api_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    # Сертификат НУЦ Минцифры — им подписаны TLS-сертификаты GigaChat
    gigachat_ca_file: str | None = str(CERTS_DIR / "russian_trusted_root_ca.crt")
    gigachat_verify_ssl: bool = True


settings = Settings()
