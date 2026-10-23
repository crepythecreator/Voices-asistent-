from urllib.parse import parse_qs, urlparse

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import OAuthAccount, User

from .conftest import login, oauth, register


def users_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(User)) or 0


# --- Почта и пароль -------------------------------------------------------------------------


def test_register_and_login_with_password(client):
    r = register(client, email="Me@Example.com")
    assert r.status_code == 201
    assert r.json()["email"] == "me@example.com" and r.json()["hasPassword"] is True
    assert client.get("/auth/me").status_code == 200

    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401
    r = client.post("/auth/login", json={"email": "ME@example.com", "password": "secret-pass"})
    assert r.status_code == 200


def test_register_rejects_duplicate_and_short_password(client):
    register(client)
    assert register(client).status_code == 409
    assert register(client, email="other@example.com", password="short").status_code == 422


def test_wrong_password_and_rate_limit(client):
    register(client)
    client.post("/auth/logout")
    for _ in range(10):
        assert client.post("/auth/login", json={"email": "me@example.com", "password": "wrong"}).status_code == 401
    # После 10 неудач блокируем даже верный пароль
    assert client.post("/auth/login", json={"email": "me@example.com", "password": "secret-pass"}).status_code == 429


def test_unknown_email_gives_same_error(client):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"})
    assert r.status_code == 401 and r.json()["detail"] == "Неверная почта или пароль"


def test_password_hash_is_not_plaintext(client):
    register(client)
    with SessionLocal() as db:
        assert db.scalar(select(User.password_hash)).startswith("$argon2")


# --- OAuth-вход -----------------------------------------------------------------------------


def test_providers_list(client):
    assert client.get("/auth/providers").json() == [
        {"id": "yandex", "title": "Яндекс ID", "configured": True},
        {"id": "google", "title": "Google", "configured": True},
    ]


def test_unconfigured_provider_is_listed_but_cannot_login(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "google_client_secret", None)
    providers = {p["id"]: p["configured"] for p in client.get("/auth/providers").json()}
    assert providers == {"yandex": True, "google": False}
    assert client.get("/auth/google/login", follow_redirects=False).status_code == 503


def test_oauth_login_requests_only_profile_scopes(client):
    r = client.get("/auth/google/login", follow_redirects=False)
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert q["scope"] == ["openid email profile"]
    assert q["code_challenge_method"] == ["S256"]
    r = client.get("/auth/yandex/login", follow_redirects=False)
    assert parse_qs(urlparse(r.headers["location"]).query)["scope"] == ["login:info login:email"]


def test_oauth_login_creates_user_and_redirects_to_next(client, monkeypatch):
    r = oauth(client, monkeypatch, "google", next_path="/settings", user_id="g1")
    assert r.headers["location"] == "http://localhost:5173/settings"
    me = client.get("/auth/me").json()
    assert me["email"] == "userg1@google.test" and me["hasPassword"] is False
    # Повторный вход — тот же пользователь
    oauth(client, monkeypatch, "google", user_id="g1")
    assert users_count() == 1


def test_oauth_links_to_existing_email_and_resets_unverified_password(client, monkeypatch):
    register(client, email="shared@example.com")
    client.post("/auth/logout")
    oauth(client, monkeypatch, "google", user_id="g1", email="shared@example.com", verified=True)
    me = client.get("/auth/me").json()
    assert users_count() == 1
    # Почта не была подтверждена — пароль мог задать кто угодно, поэтому он сброшен
    assert me["hasPassword"] is False
    client.post("/auth/logout")
    assert client.post("/auth/login", json={"email": "shared@example.com", "password": "secret-pass"}).status_code == 401


def test_unverified_provider_email_is_not_linked(client, monkeypatch):
    register(client, email="shared@example.com")
    client.post("/auth/logout")
    oauth(client, monkeypatch, "google", user_id="g1", email="shared@example.com", verified=False)
    assert users_count() == 2
    assert client.get("/auth/me").json()["email"] is None


def test_login_does_not_drop_calendar_token(client, monkeypatch, calendars):
    login(client, monkeypatch)
    oauth(client, monkeypatch, "yandex", "connect", "/settings", user_id="1001")
    client.post("/auth/logout")
    login(client, monkeypatch)  # вход запрашивает только профиль
    with SessionLocal() as db:
        assert db.scalar(select(OAuthAccount.calendar_access)) is True


def test_state_mismatch_and_denied(client):
    client.get("/auth/yandex/login", follow_redirects=False)
    r = client.get("/auth/yandex/callback", params={"code": "c", "state": "forged"}, follow_redirects=False)
    assert r.headers["location"] == "http://localhost:5173/login?error=invalid_state&provider=yandex"
    r = client.get("/auth/google/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert "error=access_denied" in r.headers["location"]


def test_open_redirect_is_blocked(client, monkeypatch):
    r = oauth(client, monkeypatch, "yandex", next_path="//evil.com")
    assert r.headers["location"] == "http://localhost:5173/"


def test_protected_endpoints_require_login(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/account/connections").status_code == 401
    assert client.post("/chat", json={"message": "привет"}).status_code == 401


# --- Подключение аккаунтов в настройках -----------------------------------------------------


def test_connect_requires_login(client, monkeypatch):
    r = oauth(client, monkeypatch, "google", "connect")
    assert r.headers["location"].startswith("http://localhost:5173/login")


def test_connect_google_calendar_to_password_account(client, monkeypatch, calendars):
    register(client)
    r = client.get("/auth/google/connect", follow_redirects=False)
    q = parse_qs(urlparse(r.headers["location"]).query)
    assert "https://www.googleapis.com/auth/calendar.app.created" in q["scope"][0]
    assert q["access_type"] == ["offline"]

    r = oauth(client, monkeypatch, "google", "connect", "/settings", user_id="g1")
    assert r.headers["location"] == "http://localhost:5173/settings?connected=google"
    conns = {c["provider"]: c for c in client.get("/account/connections").json()}
    assert conns["google"]["connected"] and conns["google"]["calendarAccess"] and conns["google"]["syncEnabled"]
    assert conns["yandex"]["connected"] is False


def test_connect_without_calendar_permission(client, monkeypatch, calendars):
    register(client)
    oauth(client, monkeypatch, "google", "connect", "/settings", user_id="g1", calendar_scope=False)
    google = next(c for c in client.get("/account/connections").json() if c["provider"] == "google")
    assert google["connected"] and not google["calendarAccess"]
    assert client.patch("/account/connections/google", json={"syncEnabled": True}).status_code == 409


def test_account_of_another_user_cannot_be_connected(client, monkeypatch, calendars):
    oauth(client, monkeypatch, "google", user_id="g1")  # первый пользователь
    client.post("/auth/logout")
    register(client, email="second@example.com")
    r = oauth(client, monkeypatch, "google", "connect", "/settings", user_id="g1")
    assert r.headers["location"] == "http://localhost:5173/settings?error=already_linked&provider=google"


def test_toggle_sync_and_disconnect(client, monkeypatch, calendars):
    register(client)
    oauth(client, monkeypatch, "yandex", "connect", "/settings", user_id="y1")
    r = client.patch("/account/connections/yandex", json={"syncEnabled": False})
    assert r.json()["syncEnabled"] is False
    assert client.delete("/account/connections/yandex").status_code == 204
    assert not next(c for c in client.get("/account/connections").json() if c["provider"] == "yandex")["connected"]


def test_cannot_disconnect_last_login_method(client, monkeypatch):
    oauth(client, monkeypatch, "google", user_id="g1")
    assert client.delete("/account/connections/google").status_code == 409
    # Задали пароль — теперь можно
    assert client.post("/account/password", json={"newPassword": "new-secret-1"}).status_code == 204
    assert client.delete("/account/connections/google").status_code == 204


def test_change_password_requires_current_and_logs_out_other_sessions(client, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    register(client)
    other = TestClient(app, base_url="http://testserver")
    other.post("/auth/login", json={"email": "me@example.com", "password": "secret-pass"})
    assert other.get("/auth/me").status_code == 200

    r = client.post("/account/password", json={"currentPassword": "wrong", "newPassword": "new-secret-1"})
    assert r.status_code == 403
    r = client.post("/account/password", json={"currentPassword": "secret-pass", "newPassword": "new-secret-1"})
    assert r.status_code == 204
    assert client.get("/auth/me").status_code == 200  # текущая сессия жива
    assert other.get("/auth/me").status_code == 401  # другие — завершены
