import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

# Настройки задаются до импорта приложения
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ.update(
    DATABASE_URL=f"sqlite:///{_db_file}",
    APP_SECRET_KEY="test-secret",
    YANDEX_CLIENT_ID="ya-client",
    YANDEX_CLIENT_SECRET="ya-secret",
    GOOGLE_CLIENT_ID="g-client",
    GOOGLE_CLIENT_SECRET="g-secret",
    # Настоящие ключи из .env тестам не нужны: внешние сервисы подменены, а лишние запросы стоят денег
    GIGACHAT_CREDENTIALS="",
    CLOUDRU_API_KEY="",
    YANDEX_API_KEY="",
    STT_PROVIDER="auto",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.account import router as account_router  # noqa: E402
from app.assistant import router as assistant_router  # noqa: E402
from app.assistant.llm import FunctionCall, LLMReply  # noqa: E402
from app.auth import router as auth_router  # noqa: E402
from app.auth.passwords import login_limiter  # noqa: E402
from app.auth.providers import PROVIDERS, Profile, TokenSet  # noqa: E402
from app.calendar import service as calendar_service  # noqa: E402
from app.db import Base, engine, utcnow  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch) -> Iterator[None]:
    Base.metadata.create_all(engine)
    # Фоновая синхронизация после входа ходила бы в настоящие календари
    monkeypatch.setattr(auth_router, "setup_calendars_in_background", lambda user_id: None)
    monkeypatch.setattr(account_router, "setup_calendars_in_background", lambda user_id: None)
    yield
    Base.metadata.drop_all(engine)
    calendar_service._busy_cache.clear()
    login_limiter._failures.clear()


@dataclass
class FakeCalendar:
    """Подмена календаря провайдера: запоминает, что ушло наружу."""

    provider: str
    saved: dict[str, str] = field(default_factory=dict)  # remote_id -> title
    deleted: list[str] = field(default_factory=list)
    external: list[Any] = field(default_factory=list)
    fail: bool = False

    def ensure_calendar(self, name: str, known_id: str | None) -> str:
        return known_id or f"{self.provider}-calendar"

    def upsert_event(self, calendar_id: str, event, remote_id: str | None) -> str:
        if self.fail:
            from app.calendar.backend import CalendarError

            raise CalendarError("Провайдер недоступен")
        rid = remote_id or f"{self.provider}-{event.id}"
        self.saved[rid] = event.title
        return rid

    def delete_event(self, calendar_id: str, remote_id: str) -> None:
        self.deleted.append(remote_id)
        self.saved.pop(remote_id, None)

    def external_events(self, start, end, exclude_id):
        return list(self.external)


@pytest.fixture
def calendars(monkeypatch) -> dict[str, FakeCalendar]:
    cals = {"yandex": FakeCalendar("yandex"), "google": FakeCalendar("google")}

    def backend_for(db, user, account):
        return cals[account.provider] if account.calendar_access else None

    monkeypatch.setattr(calendar_service, "backend_for", backend_for)
    return cals


class ScriptedLLM:
    """LLM, отвечающая заранее заданной последовательностью. Запоминает запросы."""

    def __init__(self, *replies: LLMReply):
        self.replies = list(replies)
        self.requests: list[list[dict[str, Any]]] = []

    def chat(self, messages, functions):
        self.requests.append([dict(m) for m in messages])
        return self.replies.pop(0)


def call(name: str, **arguments: Any) -> LLMReply:
    return LLMReply(content="", function_call=FunctionCall(name=name, arguments=arguments), extra={"functions_state_id": "s1"})


def text(content: str) -> LLMReply:
    return LLMReply(content=content)


@pytest.fixture
def use_llm(monkeypatch):
    def _use(llm: ScriptedLLM) -> ScriptedLLM:
        monkeypatch.setattr(assistant_router, "get_llm", lambda: llm)
        return llm

    return _use


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, base_url="http://testserver")


def fake_provider(
    monkeypatch,
    provider: str,
    user_id: str = "1001",
    email: str | None = None,
    verified: bool = True,
    calendar_scope: bool | None = None,
) -> None:
    """Подменяет запросы к провайдеру. calendar_scope=None — права как запрошены."""
    p = PROVIDERS[provider]
    email = email if email is not None else f"user{user_id}@{provider}.test"

    def exchange_code(code, verifier, with_calendar):
        granted = with_calendar if calendar_scope is None else calendar_scope
        return TokenSet(
            access_token=f"access-{provider}-{user_id}",
            refresh_token=f"refresh-{provider}-{user_id}",
            expires_at=utcnow() + timedelta(days=30),
            scope=" ".join(p.scopes(granted)),
        )

    monkeypatch.setattr(p, "exchange_code", exchange_code)
    monkeypatch.setattr(p, "fetch_profile", lambda token: Profile(user_id, email, verified, f"Тест {user_id}", None))


def oauth(client: TestClient, monkeypatch, provider: str = "yandex", action: str = "login", next_path: str = "/", **profile):
    """Проходит OAuth-поток (вход или подключение) и возвращает ответ callback."""
    fake_provider(monkeypatch, provider, **profile)
    r = client.get(f"/auth/{provider}/{action}", params={"next": next_path}, follow_redirects=False)
    assert r.status_code == 302, r.text
    location = urlparse(r.headers["location"])
    if location.netloc == "localhost:5173":  # редирект на фронт без похода к провайдеру
        return r
    state = parse_qs(location.query)["state"][0]
    return client.get(f"/auth/{provider}/callback", params={"code": "c", "state": state}, follow_redirects=False)


def login(client: TestClient, monkeypatch, yandex_id: str = "1001", next_path: str = "/") -> TestClient:
    r = oauth(client, monkeypatch, "yandex", "login", next_path, user_id=yandex_id)
    assert r.status_code == 302 and "error" not in r.headers["location"], r.headers.get("location")
    return client


def register(client: TestClient, email: str = "me@example.com", password: str = "secret-pass", name: str = "Я"):
    return client.post("/auth/register", json={"email": email, "password": password, "name": name})


@pytest.fixture
def user_client(client, monkeypatch, calendars) -> TestClient:
    """Пользователь, вошедший через Яндекс и подключивший календарь."""
    login(client, monkeypatch)
    r = oauth(client, monkeypatch, "yandex", "connect", "/settings", user_id="1001")
    assert "connected=yandex" in r.headers["location"], r.headers["location"]
    return client
