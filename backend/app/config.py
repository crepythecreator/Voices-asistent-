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

    # --- Google (OAuth) — https://console.cloud.google.com/apis/credentials ---
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str = "http://localhost:5173/api/auth/google/callback"

    # Имя отдельного календаря ассистента (Google его использует; Яндекс называет календарь по имени приложения)
    calendar_name: str = "Voices"
    caldav_url: str = "https://caldav.yandex.ru/"

    # Вход по паролю: не больше N неудачных попыток за окно (на почту и на IP)
    login_max_attempts: int = 10
    login_window_minutes: int = 15

    # --- Yandex Cloud: SpeechKit ---
    # API-ключ сервисного аккаунта с ролью ai.speechkit-stt.user
    yandex_api_key: str | None = None
    # Нужен только при авторизации IAM-токеном, для API-ключа можно не задавать
    yandex_folder_id: str | None = None

    # --- Синтез речи: GigaChat/SaluteSpeech через Cloud.ru Foundation Models (Realtime API) ---
    cloudru_api_key: str | None = None
    tts_url: str = "wss://foundation-models.api.cloud.ru/v1/realtime"
    tts_model: str = "GigaChat/SaluteSpeech"
    # Mer-Operator, Kaz-Lifelike, Tsb-Freespeech, Gli-Operator, Gli-Freespeech, Bab-Debate,
    # Bab-Energetic, Bab-Freespeech, Tsb-Hesitating
    tts_voice: str = "Mer-Operator"
    tts_speed: float = 1.0

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
