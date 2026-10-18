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
    YANDEX_CLIENT_ID="test-client",
    YANDEX_CLIENT_SECRET="test-secret",
    GIGACHAT_CREDENTIALS="",
)

from fastapi.testclient import TestClient  # noqa: E402

from app.assistant import router as assistant_router  # noqa: E402
from app.assistant.llm import FunctionCall, LLMReply  # noqa: E402
from app.auth import router as auth_router  # noqa: E402
from app.auth import yandex  # noqa: E402
from app.calendar import service as calendar_service  # noqa: E402
from app.db import Base, engine, utcnow  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db() -> Iterator[None]:
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    calendar_service._busy_cache.clear()


@dataclass
class FakeCalendar:
    """Подмена CalDAV-клиента: запоминает, что ушло в Яндекс."""

    saved: dict[str, str] = field(default_factory=dict)
    deleted: list[str] = field(default_factory=list)
    external: list[Any] = field(default_factory=list)

    def ensure_calendar(self, name: str, known_url: str | None) -> tuple[str, bool]:
        return "https://caldav.yandex.ru/calendars/test/assistant/", True

    def put_event(self, calendar_url: str, ical: str) -> None:
        uid = next(line.split(":", 1)[1] for line in ical.splitlines() if line.startswith("UID:"))
        self.saved[uid.strip()] = ical

    def delete_event(self, calendar_url: str, uid: str) -> None:
        self.deleted.append(uid)
        self.saved.pop(uid, None)

    def external_events(self, start, end, exclude_url):
        return self.external


@pytest.fixture
def fake_calendar(monkeypatch) -> FakeCalendar:
    cal = FakeCalendar()
    monkeypatch.setattr(calendar_service, "_client", lambda db, user: cal)
    return cal


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


def login(client: TestClient, monkeypatch, yandex_id: str = "1001", next_path: str = "/") -> TestClient:
    """Проходит OAuth-поток с подменёнными запросами к Яндексу."""
    monkeypatch.setattr(
        yandex,
        "exchange_code",
        lambda code, verifier: yandex.TokenSet("access-" + yandex_id, "refresh-" + yandex_id, utcnow() + timedelta(days=365), None),
    )
    monkeypatch.setattr(
        yandex,
        "fetch_profile",
        lambda token: yandex.YandexProfile(yandex_id, f"user{yandex_id}", f"user{yandex_id}@yandex.ru", "Тест", None),
    )
    monkeypatch.setattr(auth_router, "setup_calendar_in_background", lambda user_id: None)

    r = client.get("/auth/yandex/login", params={"next": next_path}, follow_redirects=False)
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    r = client.get("/auth/yandex/callback", params={"code": "c", "state": state}, follow_redirects=False)
    assert r.status_code == 302, r.text
    return client


@pytest.fixture
def user_client(client, monkeypatch) -> TestClient:
    return login(client, monkeypatch)
