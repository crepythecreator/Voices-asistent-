from urllib.parse import parse_qs, urlparse

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import User, YandexToken

from .conftest import login


def test_login_redirects_to_yandex_with_pkce(client):
    r = client.get("/auth/yandex/login", params={"next": "/calendar"}, follow_redirects=False)
    assert r.status_code == 302
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert url.netloc == "oauth.yandex.ru"
    assert q["client_id"] == ["test-client"]
    assert q["code_challenge_method"] == ["S256"]
    assert q["state"][0]
    assert "oauth_state" in r.cookies


def test_callback_creates_user_and_session(client, monkeypatch):
    login(client, monkeypatch, next_path="/calendar")
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user1001@yandex.ru"


def relogin(client, next_path: str) -> str:
    r = client.get("/auth/yandex/login", params={"next": next_path}, follow_redirects=False)
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    r = client.get("/auth/yandex/callback", params={"code": "c", "state": state}, follow_redirects=False)
    return r.headers["location"]


def test_callback_redirects_to_next_without_duplicate_user(client, monkeypatch):
    login(client, monkeypatch)
    assert relogin(client, "/calendar") == "http://localhost:5173/calendar"
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1


def test_tokens_are_stored_encrypted(user_client):
    with SessionLocal() as db:
        row = db.scalar(select(YandexToken))
    assert row is not None
    assert "access-1001" not in row.access_token_enc
    assert "refresh-1001" not in (row.refresh_token_enc or "")


def test_open_redirect_is_blocked(client, monkeypatch):
    login(client, monkeypatch)  # подменяет запросы к Яндексу
    assert relogin(client, "//evil.com") == "http://localhost:5173/"
    assert relogin(client, "https://evil.com") == "http://localhost:5173/"


def test_state_mismatch_is_rejected(client):
    client.get("/auth/yandex/login", follow_redirects=False)
    r = client.get("/auth/yandex/callback", params={"code": "c", "state": "forged"}, follow_redirects=False)
    assert r.headers["location"] == "http://localhost:5173/login?error=invalid_state"


def test_user_denied_access(client):
    r = client.get("/auth/yandex/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert r.headers["location"] == "http://localhost:5173/login?error=access_denied"


def test_logout(user_client):
    assert user_client.post("/auth/logout").status_code == 204
    assert user_client.get("/auth/me").status_code == 401


def test_protected_endpoints_require_login(client):
    assert client.get("/auth/me").status_code == 401
    assert client.post("/chat", json={"message": "привет"}).status_code == 401
    assert client.get("/events", params={"from": "2026-10-01T00:00:00Z", "to": "2026-11-01T00:00:00Z"}).status_code == 401
